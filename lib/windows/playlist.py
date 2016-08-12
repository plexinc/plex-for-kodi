import xbmc
import xbmcgui
import kodigui

import busy
import musicplayer

from lib import colors
from lib import player
from lib import util


class PlaylistWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-playlist.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_GROUP_ID = 200
    PLAYER_STATUS_BUTTON_ID = 204

    LI_AR16X9_THUMB_DIM = (178, 100)
    LI_SQUARE_THUMB_DIM = (100, 100)

    ALBUM_THUMB_DIM = (630, 630)

    PLAYLIST_LIST_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.playlist = kwargs.get('playlist')
        self.exitCommand = None

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 5)
        self.setProperties()

        self.fillPlaylist()
        self.setFocusId(self.PLAYLIST_LIST_ID)

    def onAction(self, action):
        try:
            if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()

    def playlistListClicked(self):
        mli = self.playlistListControl.getSelectedItem()
        if not mli:
            return

        if self.playlist.playlistType == 'audio':
            self.showAudioPlayer(track=mli.dataSource, playlist=self.playlist)
        elif self.playlist.playlistType == 'video':
            player.PLAYER.playVideoPlaylist(playlist=self.playlist, startpos=mli.pos())

    def showAudioPlayer(self, **kwargs):
        w = musicplayer.MusicPlayerWindow.open(**kwargs)
        del w

    def setProperties(self):
        self.setProperty(
            'background',
            self.playlist.composite.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('playlist.thumb', self.playlist.composite.asTranscodedImageURL(*self.ALBUM_THUMB_DIM))
        self.setProperty('playlist.title', self.playlist.title)
        self.setProperty('playlist.duration', util.durationToText(self.playlist.duration.asInt()))

    def createListItem(self, pi):
        if pi.type == 'track':
            return self.createTrackListItem(pi)
        elif pi.type == 'episode':
            return self.createEpisodeListItem(pi)
        elif pi.type in ('movie', 'clip'):
            return self.createMovieListItem(pi)

    def createTrackListItem(self, track):
        label2 = u'{0} / {1}'.format(track.grandparentTitle, track.parentTitle)
        mli = kodigui.ManagedListItem(track.title, label2, thumbnailImage=track.defaultThumb.asTranscodedImageURL(*self.LI_SQUARE_THUMB_DIM), data_source=track)
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(track.duration.asInt()))
        return mli

    def createEpisodeListItem(self, episode):
        label2 = u'{0} \u2022 {1}'.format(episode.grandparentTitle, u'S{0} \u2022 E{1}'.format(episode.parentIndex, episode.index))
        mli = kodigui.ManagedListItem(episode.title, label2, thumbnailImage=episode.thumb.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM), data_source=episode)
        mli.setProperty('track.duration', util.durationToShortText(episode.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', episode.isWatched and '1' or '')
        return mli

    def createMovieListItem(self, movie):
        mli = kodigui.ManagedListItem(movie.title, movie.year, thumbnailImage=movie.art.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM), data_source=movie)
        mli.setProperty('track.duration', util.durationToShortText(movie.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', movie.isWatched and '1' or '')
        return mli

    @busy.dialog()
    def fillPlaylist(self):
        items = []
        idx = 1
        for pi in self.playlist.items():
            # util.TEST('')
            mli = self.createListItem(pi)
            if mli:
                mli.setProperty('track.number', str(idx))
                mli.setProperty('plex.ID', 'PLEX-{0}'.format(pi.ratingKey))
                mli.setProperty('file', '!NONE!')
                items.append(mli)
                idx += 1

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)
