import xbmc
import xbmcgui
import kodigui
import playlist
from lib import colors
from lib import player
from lib import util


def timeDisplay(ms):
    h = ms / 3600000
    m = (ms % 3600000) / 60000
    s = (ms % 60000) / 1000
    return '{0:0>2}:{1:0>2}:{2:0>2}'.format(h, m, s)


def simplifiedTimeDisplay(ms):
    left, right = timeDisplay(ms).rsplit(':', 1)
    left = left.lstrip('0:') or '0'
    return left + ':' + right


class MusicPlayerWindow(playlist.PlaylistWindow):
    xmlFile = 'script-plex-music_player.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SEEK_BUTTON_ID = 100
    SEEK_IMAGE_ID = 200

    SEEK_IMAGE_WIDTH = 1920

    BAR_RIGHT = 1920

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.track = kwargs.get('track')
        self.album = kwargs.get('album')
        self.selectedOffset = 0

        if self.track:
            self.duration = self.track.duration.asInt()
        else:
            self.setDuration()

    def onFirstInit(self):
        self.setupSeekbar()
        self.selectionBoxMax = self.SEEK_IMAGE_WIDTH - (self.selectionBoxHalf - 3)

        self.setProperties()
        self.play()
        self.setFocusId(406)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if self.checkSeekActions(action, controlID):
                return
            elif action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SETTINGS_BUTTON_ID:
            self.showSettings()
        elif controlID == self.PLAYLIST_BUTTON_ID:
            self.showPlaylist()
        elif controlID == self.SEEK_BUTTON_ID:
            self.seekButtonClicked()

    def showSettings(self):
        pass

    def showPlaylist(self):
        w = playlist.PlaylistWindow.open()
        del w

    def setProperties(self):
        if self.track:
            self.setProperty(
                'background',
                self.album.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
            )
            self.setProperty('thumb', self.track.thumb.asTranscodedImageURL(756, 756))
        else:
            self.setProperty('background', xbmc.getInfoLabel('Player.Art(fanart)'))
            self.setProperty('thumb', xbmc.getInfoLabel('Player.Art(thumb)'))

    def play(self):
        if not self.track:
            return

        if util.trackIsPlaying(self.track):
            return

        # player.PLAYER.playAudio(self.track, window=self, fanart=self.getProperty('background'))
        player.PLAYER.playAlbum(self.album, startpos=self.track.index.asInt() - 1, window=self, fanart=self.getProperty('background'))
