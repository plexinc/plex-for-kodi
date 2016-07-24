import xbmc
import xbmcgui
import kodigui
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


class MusicPlayerWindow(kodigui.BaseDialog):
    xmlFile = 'script-plex-music_player.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    MAIN_BUTTON_ID = 100
    SEEK_IMAGE_ID = 200

    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202
    SELECTION_BOX = 203

    SETTINGS_BUTTON_ID = 403
    SKIP_BACK_BUTTON_ID = 405
    SKIP_FORWARD_BUTTON_ID = 408

    SEEK_IMAGE_WIDTH = 1920

    BAR_X = 0
    BAR_Y = 921
    BAR_RIGHT = 1920
    BAR_BOTTOM = 969

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.track = kwargs.get('track')
        self.album = kwargs.get('album')
        self.selectedOffset = 0

        if self.track:
            self.duration = self.track.duration.asInt()
        else:
            try:
                self.duration = player.PLAYER.getTotalTime() * 1000
            except RuntimeError:  # Not playing
                self.duration = 0

    def onFirstInit(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(self.SELECTION_BOX)

        self.setProperties()
        self.play()
        self.setFocusId(406)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if controlID == self.MAIN_BUTTON_ID:
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
        if controlID == self.SETTINGS_BUTTON_ID:
            self.showSettings()
        elif controlID == self.MAIN_BUTTON_ID:
            xbmc.Player().seekTime(self.selectedOffset / 1000.0)

    def onFocus(self, controlID):
        if controlID == self.MAIN_BUTTON_ID:
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
        elif w > 1869:
            self.selectionBox.setPosition(-100 + (1920 - w), 0)
        else:
            self.selectionBox.setPosition(-50, 0)
        self.setProperty('time.selection', util.simplifiedTimeDisplay(int(self.selectedOffset)))

    def showSettings(self):
        pass

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

        player.PLAYER.playAudio(self.track, window=self, fanart=self.getProperty('background'))
