import xbmc
import xbmcgui
import kodigui

import busy
import windowutils
import dropdown
import opener

from lib import util
from lib import player
from lib import kodijsonrpc

from lib.util import T


class CurrentPlaylistWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-music_current_playlist.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    LI_THUMB_DIM = (64, 64)
    ALBUM_THUMB_DIM = (639, 639)

    PLAYLIST_LIST_ID = 101

    SEEK_BUTTON_ID = 500
    SEEK_IMAGE_ID = 510

    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202
    SELECTION_BOX = 203

    REPEAT_BUTTON_ID = 401
    SHUFFLE_BUTTON_ID = 402
    SHUFFLE_REMOTE_BUTTON_ID = 422
    SKIP_PREV_BUTTON_ID = 404
    SKIP_NEXT_BUTTON_ID = 409
    PLAYLIST_BUTTON_ID = 410
    OPTIONS_BUTTON_ID = 411

    SEEK_IMAGE_WIDTH = 819
    SELECTION_BOX_WIDTH = 101
    SELECTION_INDICATOR_Y = 896

    BAR_X = 0
    BAR_Y = 921
    BAR_RIGHT = 819
    BAR_BOTTOM = 969

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.selectedOffset = 0
        self.setDuration()
        self.exitCommand = None

    def doClose(self, **kwargs):
        player.PLAYER.off('playback.started', self.onPlayBackStarted)
        player.PLAYER.off('playlist.changed', self.playQueueCallback)
        if player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            player.PLAYER.handler.playQueue.off('change', self.updateProperties)
        kodigui.ControlledWindow.doClose(self)

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 9)
        self.setupSeekbar()

        self.fillPlaylist()
        self.selectPlayingItem()
        self.setFocusId(self.PLAYLIST_LIST_ID)

        self.updateProperties()
        if player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            player.PLAYER.handler.playQueue.on('change', self.updateProperties)
        player.PLAYER.on('playlist.changed', self.playQueueCallback)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if self.checkSeekActions(action, controlID):
                return
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.SEEK_BUTTON_ID:
            self.seekButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.fillPlaylist()
        elif controlID == self.SHUFFLE_REMOTE_BUTTON_ID:
            player.PLAYER.handler.playQueue.setShuffle()
        elif controlID == self.REPEAT_BUTTON_ID:
            self.repeatButtonClicked()
        elif controlID == self.SKIP_PREV_BUTTON_ID:
            self.skipPrevButtonClicked()
        elif controlID == self.SKIP_NEXT_BUTTON_ID:
            self.skipNextButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()

    def onFocus(self, controlID):
        if controlID == self.SEEK_BUTTON_ID:
            try:
                if player.PLAYER.isPlaying():
                    self.selectedOffset = player.PLAYER.getTime() * 1000
                else:
                    self.selectedOffset = 0
            except RuntimeError:
                self.selectedOffset = 0

            self.updateSelectedProgress()

    def onPlayBackStarted(self, **kwargs):
        self.setDuration()

    def repeatButtonClicked(self):
        if player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            if xbmc.getCondVisibility('Playlist.IsRepeatOne'):
                xbmc.executebuiltin('PlayerControl(RepeatOff)')
            elif player.PLAYER.handler.playQueue.isRepeat:
                player.PLAYER.handler.playQueue.setRepeat(False)
                player.PLAYER.handler.playQueue.refresh(force=True)
                xbmc.executebuiltin('PlayerControl(RepeatOne)')
            else:
                player.PLAYER.handler.playQueue.setRepeat(True)
                player.PLAYER.handler.playQueue.refresh(force=True)
        else:
            xbmc.executebuiltin('PlayerControl(Repeat)')

    def skipPrevButtonClicked(self):
        if not xbmc.getCondVisibility('MusicPlayer.HasPrevious') and player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue:
            util.DEBUG_LOG('MusicPlayer: No previous in Kodi playlist - refreshing remote PQ')
            if not player.PLAYER.handler.playQueue.refresh(force=True, wait=True):
                return

        xbmc.executebuiltin('PlayerControl(Previous)')

    def skipNextButtonClicked(self):
        if not xbmc.getCondVisibility('MusicPlayer.HasNext') and player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            util.DEBUG_LOG('MusicPlayer: No next in Kodi playlist - refreshing remote PQ')
            if not player.PLAYER.handler.playQueue.refresh(force=True, wait=True):
                return

        xbmc.executebuiltin('PlayerControl(Next)')

    def optionsButtonClicked(self, pos=(670, 1060)):
        track = player.PLAYER.currentTrack()
        if not track:
            return

        options = []

        options.append({'key': 'to_album', 'display': T(32300, 'Go to Album')})
        options.append({'key': 'to_artist', 'display': T(32301, 'Go to Artist')})
        options.append({'key': 'to_section', 'display': T(32302, u'Go to {0}').format(track.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, pos, close_direction='down', pos_is_bottom=True, close_on_playback_ended=True)
        if not choice:
            return

        if choice['key'] == 'to_album':
            self.processCommand(opener.open(track.parentRatingKey))
        elif choice['key'] == 'to_artist':
            self.processCommand(opener.open(track.grandparentRatingKey))
        elif choice['key'] == 'to_section':
            self.goHome(track.getLibrarySectionId())

    def selectPlayingItem(self):
        for mli in self.playlistListControl:
            if xbmc.getCondVisibility('SubString(MusicPlayer.Comment,{0},Left)'.format(mli.dataSource['comment'].split(':', 1)[0])):
                self.playlistListControl.selectItem(mli.pos())
                break

    def playQueueCallback(self, **kwargs):
        self.setProperty('pq.isshuffled', player.PLAYER.handler.playQueue.isShuffled and '1' or '')
        mli = self.playlistListControl.getSelectedItem()
        pi = mli.dataSource
        plexID = pi['comment'].split(':', 1)[0]
        viewPos = self.playlistListControl.getViewPosition()

        self.fillPlaylist()

        for ni in self.playlistListControl:
            if ni.dataSource['comment'].split(':', 1)[0] == plexID:
                self.playlistListControl.selectItem(ni.pos())
                break

        xbmc.sleep(100)

        newViewPos = self.playlistListControl.getViewPosition()
        if viewPos != newViewPos:
            diff = newViewPos - viewPos
            self.playlistListControl.shiftView(diff, True)

    def seekButtonClicked(self):
        player.PLAYER.seekTime(self.selectedOffset / 1000.0)

    def playlistListClicked(self):
        mli = self.playlistListControl.getSelectedItem()
        if not mli:
            return
        player.PLAYER.playselected(mli.pos())

    def createListItem(self, pi, idx):
        label2 = '{0} / {1}'.format(pi['artist'][0], pi['album'])
        plexInfo = pi['comment']
        mli = kodigui.ManagedListItem(pi['title'], label2, thumbnailImage=pi['thumbnail'], data_source=pi)
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(pi['duration'] * 1000))
        if plexInfo.startswith('PLEX-'):
            mli.setProperty('track.ID', plexInfo.split('-', 1)[-1].split(':', 1)[0])
            mli.setProperty('track.number', str(pi['playcount']))
        else:
            mli.setProperty('track.ID', '!NONE!')
            mli.setProperty('track.number', str(pi['track']))
            mli.setProperty('playlist.position', str(idx))

        mli.setProperty('file', pi['file'])
        return mli

    @busy.dialog()
    def fillPlaylist(self):
        items = []
        idx = 1
        for pi in kodijsonrpc.rpc.PlayList.GetItems(
            playlistid=xbmc.PLAYLIST_MUSIC, properties=['title', 'artist', 'album', 'track', 'thumbnail', 'duration', 'playcount', 'comment', 'file']
        )['items']:
            mli = self.createListItem(pi, idx)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)

    def setupSeekbar(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(self.SELECTION_BOX)
        self.selectionBoxHalf = self.SELECTION_BOX_WIDTH / 2
        self.selectionBoxMax = self.SEEK_IMAGE_WIDTH
        player.PLAYER.on('playback.started', self.onPlayBackStarted)

    def checkSeekActions(self, action, controlID):
        if controlID == self.SEEK_BUTTON_ID:
            if action == xbmcgui.ACTION_MOUSE_MOVE:
                self.seekMouse(action)
                return True
            elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_NEXT_ITEM):
                self.seekForward(3000)
                return True
            elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_PREV_ITEM):
                self.seekBack(3000)
                return True
            # elif action == xbmcgui.ACTION_MOVE_UP:
            #     self.seekForward(60000)
            # elif action == xbmcgui.ACTION_MOVE_DOWN:
            #     self.seekBack(60000)

    def setDuration(self):
        try:
            self.duration = player.PLAYER.getTotalTime() * 1000
        except RuntimeError:  # Not playing
            self.duration = 0

    def seekForward(self, offset):
        self.selectedOffset += offset
        if self.selectedOffset > self.duration:
            self.selectedOffset = self.duration

        self.updateSelectedProgress()

    def seekBack(self, offset):
        self.selectedOffset -= offset
        if self.selectedOffset < 0:
            self.selectedOffset = 0

        self.updateSelectedProgress()

    def seekMouse(self, action):
        x = self.mouseXTrans(action.getAmount1())
        y = self.mouseXTrans(action.getAmount2())
        if not (self.BAR_Y <= y <= self.BAR_BOTTOM):
            return

        if not (self.BAR_X <= x <= self.BAR_RIGHT):
            return

        self.selectedOffset = int((x - self.BAR_X) / float(self.SEEK_IMAGE_WIDTH) * self.duration)
        self.updateSelectedProgress()

    def updateSelectedProgress(self):
        ratio = self.selectedOffset / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        self.seekbarControl.setWidth(w or 1)

        self.selectionIndicator.setPosition(w, self.SELECTION_INDICATOR_Y)
        if w < self.selectionBoxHalf - 3:
            self.selectionBox.setPosition((-self.selectionBoxHalf + (self.selectionBoxHalf - w)) - 3, 0)
        elif w > self.selectionBoxMax:
            self.selectionBox.setPosition((-self.SELECTION_BOX_WIDTH + (self.SEEK_IMAGE_WIDTH - w)) + 3, 0)
        else:
            self.selectionBox.setPosition(-self.selectionBoxHalf, 0)
        self.setProperty('time.selection', util.simplifiedTimeDisplay(int(self.selectedOffset)))

    def updateProperties(self, **kwargs):
        pq = player.PLAYER.handler.playQueue
        if pq:
            if pq.isRemote:
                self.setProperty('pq.isRemote', '1')
                self.setProperty('pq.hasnext', pq.allowSkipNext and '1' or '')
                self.setProperty('pq.hasprev', pq.allowSkipPrev and '1' or '')
                self.setProperty('pq.repeat', pq.isRepeat and '1' or '')
                self.setProperty('pq.shuffled', pq.isShuffled and '1' or '')
            else:
                self.setProperties(('pq.isRemote', 'pq.hasnext', 'pq.hasprev', 'pq.repeat', 'pq.shuffled'), '')
