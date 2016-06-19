import re
import xbmcgui
import kodigui
from lib import util


class SeekDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-seek_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    MAIN_BUTTON_ID = 100
    SEEK_IMAGE_ID = 200
    BIF_IMAGE_ID = 300
    SEEK_IMAGE_WIDTH = 1600

    BAR_X = 150
    BAR_Y = 820
    BAR_RIGHT = 1760
    BAR_BOTTOM = 850

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.handler = kwargs.get('handler')
        self.bifURL = None
        self.baseURL = None
        self.baseOffset = 0
        self.duration = 0
        self.offset = 0
        self.selectedOffset = 0
        self.initialized = False

    def trueOffset(self):
        return self.baseOffset + self.offset

    def onFirstInit(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.bifImageControl = self.getControl(self.BIF_IMAGE_ID)
        self.setFocusId(self.MAIN_BUTTON_ID)
        self.initialized = True
        self.update()

    def onReInit(self):
        self.updateProgress()

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_MOVE_RIGHT:
                self.seekForward(10000)
            elif action == xbmcgui.ACTION_MOVE_LEFT:
                self.seekBack(10000)
            if action == xbmcgui.ACTION_MOVE_UP:
                self.seekForward(60000)
            elif action == xbmcgui.ACTION_MOVE_DOWN:
                self.seekBack(60000)
            elif action == xbmcgui.ACTION_MOUSE_MOVE:
                self.seekMouse(action)
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        self.handler.seek(self.selectedOffset)
        self.doClose()

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

    def setup(self, duration, offset=0, bif_url=None):
        self.baseOffset = offset
        self.offset = 0
        self.duration = duration
        self.bifURL = bif_url
        self.baseURL = re.sub('/\d+\?', '/{0}?', self.bifURL)
        self.update()

    def update(self, offset=None):
        if offset is not None:
            self.offset = offset
            self.selectedOffset = self.trueOffset()

        self.updateProgress()

    def updateProgress(self):
        if not self.initialized:
            return

        ratio = self.selectedOffset / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        # bifx = (w - int(ratio * 320)) + 40
        bifx = w
        self.setProperty('bif.image', self.baseURL.format(self.selectedOffset))
        self.seekbarControl.setWidth(w)
        self.bifImageControl.setPosition(bifx, 600)
