import xbmc
import xbmcgui
import kodigui

from lib import util
from lib import player
import musicplayer


class PlaylistWindow(kodigui.BaseDialog):
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

    SHUFFLE_BUTTON_ID = 402
    SETTINGS_BUTTON_ID = 403
    SKIP_BACK_BUTTON_ID = 405
    SKIP_FORWARD_BUTTON_ID = 408
    PLAYLIST_BUTTON_ID = 410

    SEEK_IMAGE_WIDTH = 819

    BAR_X = 0
    BAR_Y = 921
    BAR_RIGHT = 819
    BAR_BOTTOM = 969

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.selectedOffset = 0
        try:
            self.duration = player.PLAYER.getTotalTime() * 1000
        except RuntimeError:  # Not playing
            self.duration = 0
        self.exitCommand = None

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 5)
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(self.SELECTION_BOX)

        self.fillPlaylist()
        self.setFocusId(self.PLAYLIST_LIST_ID)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if controlID == self.SEEK_BUTTON_ID:
                if action == xbmcgui.ACTION_MOUSE_MOVE:
                    return self.seekMouse(action)
                elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_NEXT_ITEM):
                    return self.seekForward(3000)
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_PREV_ITEM):
                    return self.seekBack(3000)
                # elif action == xbmcgui.ACTION_MOVE_UP:
                #     self.seekForward(60000)
                # elif action == xbmcgui.ACTION_MOVE_DOWN:
                #     self.seekBack(60000)

            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.SEEK_BUTTON_ID:
            xbmc.Player().seekTime(self.selectedOffset / 1000.0)
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.fillPlaylist()

    def onFocus(self, controlID):
        if controlID == self.SEEK_BUTTON_ID:
            self.selectedOffset = xbmc.Player().getTime() * 1000
            self.updateSelectedProgress()

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
        self.seekbarControl.setWidth(w)

        self.selectionIndicator.setPosition(w, 896)
        if w < 51:
            self.selectionBox.setPosition(-50 + (50 - w), 0)
        elif w > 768:
            self.selectionBox.setPosition(-100 + (819 - w), 0)
        else:
            self.selectionBox.setPosition(-50, 0)
        self.setProperty('time.selection', util.simplifiedTimeDisplay(int(self.selectedOffset)))

    def showAudioPlayer(self):
        import musicplayer
        w = musicplayer.MusicPlayerWindow.open()
        del w

    def playlistListClicked(self):
        mli = self.playlistListControl.getSelectedItem()
        if not mli:
            return

        w = musicplayer.MusicPlayerWindow.open(track=mli.dataSource, album=self.season)
        del w

    def createListItem(self, li):
        tag = li.getMusicInfoTag()
        mli = kodigui.ManagedListItem(
            tag.getTitle() or li.getLabel(), thumbnailImage='', data_source=li
        )
        mli.setProperty('track.number', str(tag.getTrack()))
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(tag.getDuration() * 1000))
        mli.setProperty('artist', str(tag.getArtist()))
        mli.setProperty('album', str(tag.getAlbum()))
        mli.setProperty('disc', str(tag.getDisc()))
        mli.setProperty('number', '{0:0>2}'.format(tag.getTrack()))
        # util.TEST('{0} {1} {2} {3}'.format(tag.getArtist(), tag.getAlbum(), tag.getDisc(), tag.getTrack()))
        # util.TEST('{0} {1} {2} {3}'.format(
        #     xbmc.getInfoLabel('MusicPlayer.Artist'),
        #     xbmc.getInfoLabel('MusicPlayer.Album'),
        #     xbmc.getInfoLabel('MusicPlayer.DiscNumber'),
        #     xbmc.getInfoLabel('MusicPlayer.TrackNumber'))
        # )
        return mli

    def fillPlaylist(self):
        items = []
        idx = 0
        plist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        for i in range(len(plist)):
            li = plist[i]
            util.TEST(li.getArt('thumb'))
            mli = self.createListItem(li)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)
