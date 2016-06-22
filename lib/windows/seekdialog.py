import re
import time
import xbmcgui
import kodigui
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


class SeekDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-seek_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    MAIN_BUTTON_ID = 100
    SEEK_IMAGE_ID = 200
    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202
    BIF_IMAGE_ID = 300
    SEEK_IMAGE_WIDTH = 1920

    BAR_X = 0
    BAR_Y = 921
    BAR_RIGHT = 1920
    BAR_BOTTOM = 969

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.handler = kwargs.get('handler')
        self.bifURL = None
        self.baseURL = None
        self.hasBif = bool(self.bifURL)
        self.baseOffset = 0
        self.duration = 0
        self.offset = 0
        self.selectedOffset = 0
        self.title = ''
        self.title2 = ''
        self.fromSeek = False
        self.initialized = False

    def trueOffset(self):
        return self.baseOffset + self.offset

    def onFirstInit(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.positionControl = self.getControl(self.POSITION_IMAGE_ID)
        self.bifImageControl = self.getControl(self.BIF_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(203)
        self.initialized = True
        self.setProperties()
        self.update()

    def onReInit(self):
        self.setProperties()
        self.updateProgress()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if controlID == self.MAIN_BUTTON_ID:
                if action == xbmcgui.ACTION_MOVE_RIGHT:
                    return self.seekForward(10000)
                elif action == xbmcgui.ACTION_MOVE_LEFT:
                    return self.seekBack(10000)
                # elif action == xbmcgui.ACTION_MOVE_UP:
                #     self.seekForward(60000)
                # elif action == xbmcgui.ACTION_MOVE_DOWN:
                #     self.seekBack(60000)
                elif action == xbmcgui.ACTION_MOUSE_MOVE:
                    return self.seekMouse(action)

            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                self.doClose()
                self.handler.onSeekAborted()
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onFocus(self, controlID):
        if controlID == self.MAIN_BUTTON_ID:
            self.selectedOffset = self.trueOffset()
            self.updateProgress()

    def onClick(self, controlID):
        if controlID == self.MAIN_BUTTON_ID:
            self.handler.seek(self.selectedOffset)
            self.doClose()

    def setProperties(self):
        if self.fromSeek:
            self.setFocusId(self.MAIN_BUTTON_ID)
        else:
            self.setFocusId(400)

        self.setProperty('has.bif', self.bifURL and '1' or '')
        self.setProperty('video.title', self.title)
        self.setProperty('video.title2', self.title2)
        self.setProperty('time.duration', timeDisplay(self.duration))
        self.updateCurrent()

    def updateCurrent(self):
        ratio = self.trueOffset() / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        self.positionControl.setWidth(w)
        to = self.trueOffset()
        self.setProperty('time.current', timeDisplay(to))
        self.setProperty('time.end', time.strftime('%I:%M %p', time.localtime(time.time() + ((self.duration - to) / 1000))).lstrip('0'))

    def seekForward(self, offset):
        self.selectedOffset += offset
        if self.selectedOffset > self.duration:
            self.selectedOffset = self.duration

        self.updateProgress()

    def seekBack(self, offset):
        self.selectedOffset -= offset
        if self.selectedOffset < 0:
            self.selectedOffset = 0

        self.updateProgress()

    def seekMouse(self, action):
        x = self.mouseXTrans(action.getAmount1())
        y = self.mouseXTrans(action.getAmount2())
        if not (self.BAR_Y <= y <= self.BAR_BOTTOM):
            return

        if not (self.BAR_X <= x <= self.BAR_RIGHT):
            return

        self.selectedOffset = int((x - self.BAR_X) / float(self.SEEK_IMAGE_WIDTH) * self.duration)
        self.updateProgress()

    def setup(self, duration, offset=0, bif_url=None, title='', title2=''):
        self.title = title
        self.title2 = title2
        self.setProperty('video.title', title)
        self.baseOffset = offset
        self.offset = 0
        self.duration = duration
        self.bifURL = bif_url
        self.hasBif = bool(self.bifURL)
        if self.hasBif:
            self.baseURL = re.sub('/\d+\?', '/{0}?', self.bifURL)
        self.update()

    def update(self, offset=None, from_seek=False):
        self.fromSeek = from_seek
        if offset is not None:
            self.offset = offset
            self.selectedOffset = self.trueOffset()

        self.updateProgress()

    def updateProgress(self):
        if not self.initialized:
            return

        ratio = self.selectedOffset / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        bifx = (w - int(ratio * 324)) + self.BAR_X
        # bifx = w
        self.selectionIndicator.setPosition(w, 896)
        if w < 51:
            self.selectionBox.setPosition(-50 + (50 - w), 0)
        elif w > 1869:
            self.selectionBox.setPosition(-100 + (1920 - w), 0)
        else:
            self.selectionBox.setPosition(-50, 0)
        self.setProperty('time.selection', simplifiedTimeDisplay(self.selectedOffset))
        if self.hasBif:
            self.setProperty('bif.image', self.baseURL.format(self.selectedOffset))
            self.bifImageControl.setPosition(bifx, 752)

        self.seekbarControl.setWidth(w)

    def tick(self):
        if not self.initialized:
            return
        try:
            self.offset = int(self.handler.player.getTime() * 1000)
        except RuntimeError:  # Playback has stopped
            return

        self.updateCurrent()
