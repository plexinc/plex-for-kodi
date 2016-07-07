import xbmc
import xbmcgui
import kodigui
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


class MusicPlayerWindow(kodigui.BaseDialog):
    xmlFile = 'script-plex-music_player.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202

    SETTINGS_BUTTON_ID = 403
    SKIP_BACK_BUTTON_ID = 405
    SKIP_FORWARD_BUTTON_ID = 408

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.track = kwargs.get('track')

    def onFirstInit(self):
        self.setProperties()
        self.play()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if controlID == 9999:  # self.MAIN_BUTTON_ID:
                if action == xbmcgui.ACTION_MOUSE_MOVE:
                    return self.seekMouse(action)
                elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_NEXT_ITEM):
                    return self.seekForward(10000)
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_PREV_ITEM):
                    return self.seekBack(10000)
                elif action == xbmcgui.ACTION_MOVE_DOWN:
                    self.updateBigSeek()
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
        if controlID == self.SETTINGS_BUTTON_ID:
            self.showSettings()

    def showSettings(self):
        pass

    def setProperties(self):
        self.setProperty('thumb', self.track.thumb.asTranscodedImageURL(756, 756))

    def play(self):
        player.PLAYER.playAudio(self.track)
