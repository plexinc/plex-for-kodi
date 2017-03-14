import threading

import xbmc
import xbmcgui
import kodigui

import busy
import videoplayer
import windowutils
import dropdown
import search
import plexnet
import opener

from lib import colors
from lib import util
from lib import player
from lib import backgroundthread

from lib.util import T

PLAYLIST_PAGE_SIZE = 500
PLAYLIST_INITIAL_SIZE = 100


class ChunkRequestTask(backgroundthread.Task):
    WINDOW = None

    @classmethod
    def reset(cls):
        del cls.WINDOW
        cls.WINDOW = None

    def setup(self, start, size):
        self.start = start
        self.size = size
        return self

    def contains(self, pos):
        return self.start <= pos <= (self.start + self.size)

    def run(self):
        if self.isCanceled():
            return

        try:
            items = self.WINDOW.playlist.extend(self.start, self.size)
            if self.isCanceled():
                return

            if not self.WINDOW:  # Window is closed
                return

            self.WINDOW.chunkCallback(items, self.start)
        except AttributeError:
            util.DEBUG_LOG('Playlist window closed, ignoring chunk at index {0}'.format(self.start))
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on playlist: {0}'.format(repr(self.WINDOW.playlist.title)))


class PlaylistWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-playlist.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_GROUP_ID = 200
    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303

    LI_AR16X9_THUMB_DIM = (178, 100)
    LI_SQUARE_THUMB_DIM = (100, 100)

    ALBUM_THUMB_DIM = (630, 630)

    PLAYLIST_LIST_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.playlist = kwargs.get('playlist')
        self.exitCommand = None
        self.tasks = backgroundthread.Tasks()
        self.isPlaying = False
        ChunkRequestTask.WINDOW = self

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 5)
        self.setProperties()

        self.fillPlaylist()
        self.setFocusId(self.PLAYLIST_LIST_ID)

    # def onAction(self, action):
    #     try:
    #         if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
    #             if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
    #                 self.setFocusId(self.OPTIONS_GROUP_ID)
    #                 return
    #     except:
    #         util.ERROR()

    #     kodigui.ControlledWindow.onAction(self, action)

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.doClose()
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playlistListClicked(no_item=True, shuffle=False)
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.playlistListClicked(no_item=True, shuffle=True)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def doClose(self):
        kodigui.ControlledWindow.doClose(self)
        self.tasks.cancel()
        ChunkRequestTask.reset()

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self))

    def playlistListClicked(self, no_item=False, shuffle=False):
        if no_item:
            mli = None
        else:
            mli = self.playlistListControl.getSelectedItem()
            if not mli or not mli.dataSource:
                return

        try:
            self.isPlaying = True
            self.tasks.cancel()
            player.PLAYER.stop()  # Necessary because if audio is already playing, it will close the window when that is stopped
            if self.playlist.playlistType == 'audio':
                if self.playlist.leafCount.asInt() <= PLAYLIST_INITIAL_SIZE:
                    self.playlist.setShuffle(shuffle)
                    self.playlist.setCurrent(mli and mli.pos() or 0)
                    self.showAudioPlayer(track=mli and mli.dataSource or self.playlist.current(), playlist=self.playlist)
                else:
                    args = {'sourceType': '8', 'shuffle': shuffle}
                    if mli:
                        args['key'] = mli.dataSource.key
                    pq = plexnet.playqueue.createPlayQueueForItem(self.playlist, options=args)
                    opener.open(pq)
            elif self.playlist.playlistType == 'video':
                if self.playlist.leafCount.asInt() <= PLAYLIST_INITIAL_SIZE:
                    self.playlist.setShuffle(shuffle)
                    self.playlist.setCurrent(mli and mli.pos() or 0)
                    videoplayer.play(play_queue=self.playlist)
                else:
                    args = {'shuffle': shuffle}
                    if mli:
                        args['key'] = mli.dataSource.key
                    pq = plexnet.playqueue.createPlayQueueForItem(self.playlist, options=args)
                    opener.open(pq)

        finally:
            self.isPlaying = False
            self.restartFill()

    def restartFill(self):
        threading.Thread(target=self._restartFill).start()

    def _restartFill(self):
        util.DEBUG_LOG('Checking if playlist list is full...')
        for idx, mli in enumerate(self.playlistListControl):
            if self.isPlaying or not self.isOpen or util.MONITOR.abortRequested():
                break

            if not mli.dataSource:
                if self.playlist[idx]:
                    self.updateListItem(idx, self.playlist[idx])
                else:
                    break
        else:
            util.DEBUG_LOG('Playlist list is full - nothing to do')
            return

        util.DEBUG_LOG('Playlist list is not full - finishing')
        total = self.playlist.leafCount.asInt()
        for start in range(idx, total, PLAYLIST_PAGE_SIZE):
            if util.MONITOR.abortRequested():
                break
            self.tasks.add(ChunkRequestTask().setup(start, PLAYLIST_PAGE_SIZE))

        backgroundthread.BGThreader.addTasksToFront(self.tasks)

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        if not options:
            return

        choice = dropdown.showDropdown(options, (440, 1020), close_direction='down', pos_is_bottom=True, close_on_playback_ended=True)
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')

    def setProperties(self):
        self.setProperty(
            'background',
            self.playlist.composite.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('playlist.thumb', self.playlist.composite.asTranscodedImageURL(*self.ALBUM_THUMB_DIM))
        self.setProperty('playlist.title', self.playlist.title)
        self.setProperty('playlist.duration', util.durationToText(self.playlist.duration.asInt()))

    def updateListItem(self, idx, pi, mli=None):
        mli = mli or self.playlistListControl.getListItem(idx)
        mli.setLabel(pi.title)
        mli.setProperty('track.ID', pi.ratingKey)
        mli.setProperty('track.number', str(idx + 1))
        mli.dataSource = pi

        if pi.type == 'track':
            self.createTrackListItem(mli, pi)
        elif pi.type == 'episode':
            self.createEpisodeListItem(mli, pi)
        elif pi.type in ('movie', 'clip'):
            self.createMovieListItem(mli, pi)

        return mli

    def createTrackListItem(self, mli, track):
        mli.setLabel2(u'{0} / {1}'.format(track.grandparentTitle, track.parentTitle))
        mli.setThumbnailImage(track.defaultThumb.asTranscodedImageURL(*self.LI_SQUARE_THUMB_DIM))
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(track.duration.asInt()))

    def createEpisodeListItem(self, mli, episode):
        label2 = u'{0} \u2022 {1}'.format(
            episode.grandparentTitle, u'{0}{1} \u2022 {2}{3}'.format(T(32310, 'S'), episode.parentIndex, T(32311, 'E'), episode.index)
        )
        mli.setLabel2(label2)
        mli.setThumbnailImage(episode.thumb.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM))
        mli.setProperty('track.duration', util.durationToShortText(episode.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', episode.isWatched and '1' or '')

    def createMovieListItem(self, mli, movie):
        mli.setLabel2(movie.year)
        mli.setThumbnailImage(movie.art.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM))
        mli.setProperty('track.duration', util.durationToShortText(movie.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', movie.isWatched and '1' or '')

    @busy.dialog()
    def fillPlaylist(self):
        total = self.playlist.leafCount.asInt()

        endoffirst = min(PLAYLIST_INITIAL_SIZE, PLAYLIST_PAGE_SIZE, total)
        items = [self.updateListItem(i, pi, kodigui.ManagedListItem()) for i, pi in enumerate(self.playlist.extend(0, endoffirst))]

        items += [kodigui.ManagedListItem() for i in range(total - endoffirst)]

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)

        if total <= min(PLAYLIST_INITIAL_SIZE, PLAYLIST_PAGE_SIZE):
            return

        for start in range(endoffirst, total, PLAYLIST_PAGE_SIZE):
            if util.MONITOR.abortRequested():
                break
            self.tasks.add(ChunkRequestTask().setup(start, PLAYLIST_PAGE_SIZE))

        backgroundthread.BGThreader.addTasksToFront(self.tasks)

    def chunkCallback(self, items, start):
        for i, pi in enumerate(items):
            if self.isPlaying or not self.isOpen or util.MONITOR.abortRequested():
                break

            idx = start + i
            self.updateListItem(idx, pi)
