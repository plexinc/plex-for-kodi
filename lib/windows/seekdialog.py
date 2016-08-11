import re
import time
import xbmc
import xbmcgui
import kodigui
import playersettings
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
    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202
    BIF_IMAGE_ID = 300
    SEEK_IMAGE_WIDTH = 1920

    SETTINGS_BUTTON_ID = 403
    PREV_BUTTON_ID = 404
    SKIP_BACK_BUTTON_ID = 405
    SKIP_FORWARD_BUTTON_ID = 408
    NEXT_BUTTON_ID = 409

    BAR_X = 0
    BAR_Y = 921
    BAR_RIGHT = 1920
    BAR_BOTTOM = 969

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.handler = kwargs.get('handler')
        self.initialVideoSettings = {}
        self.initialAudioStream = None
        self.initialSubtitleStream = None
        self.bifURL = None
        self.baseURL = None
        self.hasBif = bool(self.bifURL)
        self.baseOffset = 0
        self.duration = 0
        self.offset = 0
        self.selectedOffset = 0
        self.bigSeekOffset = 0
        self.title = ''
        self.title2 = ''
        self.fromSeek = False
        self.initialized = False

    @property
    def player(self):
        return self.handler.player

    def trueOffset(self):
        if self.handler.mode == self.handler.MODE_ABSOLUTE:
            return self.offset
        else:
            return self.baseOffset + self.offset

    def onFirstInit(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.positionControl = self.getControl(self.POSITION_IMAGE_ID)
        self.bifImageControl = self.getControl(self.BIF_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(203)
        self.bigSeekControl = kodigui.ManagedControlList(self, 500, 12)
        self.initialized = True
        self.setProperties()
        self.videoSettingsHaveChanged()
        self.update()

    def onReInit(self):
        self.setProperties()
        self.videoSettingsHaveChanged()
        self.updateProgress()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if controlID == self.MAIN_BUTTON_ID:
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
            elif controlID == 500:
                if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_NEXT_ITEM):
                    return self.updateBigSeek()
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_PREV_ITEM):
                    return self.updateBigSeek()

            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                self.handler.onSeekAborted()
                return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onFocus(self, controlID):
        if controlID == self.MAIN_BUTTON_ID:
            self.selectedOffset = self.trueOffset()
            self.updateProgress()
        elif controlID == 500:
            self.setBigSeekShift()
            self.updateBigSeek()

    def onClick(self, controlID):
        if controlID == self.MAIN_BUTTON_ID:
            self.handler.seek(self.selectedOffset)
            self.doClose()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.showSettings()
        elif controlID == self.PREV_BUTTON_ID:
            self.handler.prev()
        elif controlID == self.NEXT_BUTTON_ID:
            self.handler.next()
        elif controlID == 500:
            self.bigSeekSelected()

    def videoSettingsHaveChanged(self):
        if (
            self.player.video.settings.prefOverrides != self.initialVideoSettings or
            self.player.video.selectedAudioStream() != self.initialAudioStream or
            self.player.video.selectedSubtitleStream() != self.initialSubtitleStream
        ):
            self.initialVideoSettings = dict(self.player.video.settings.prefOverrides)
            self.initialAudioStream = self.player.video.selectedAudioStream()
            self.initialSubtitleStream = self.player.video.selectedSubtitleStream()
            return True

        return False

    def showSettings(self):
        playersettings.showDialog(self.player.video)
        if self.videoSettingsHaveChanged():
            self.handler.seek(self.trueOffset(), settings_changed=True)
            self.doClose()

    def setBigSeekShift(self):
        for mli in self.bigSeekControl:
            if mli.dataSource > self.selectedOffset:
                break
            closest = mli
        self.bigSeekOffset = self.selectedOffset - closest.dataSource
        pxOffset = int(self.bigSeekOffset / float(self.duration) * 1920)
        self.bigSeekControl.setPosition(-8 + pxOffset, 937)
        self.bigSeekControl.selectItem(closest.pos())
        xbmc.sleep(100)

    def updateBigSeek(self):
        self.selectedOffset = self.bigSeekControl.getSelectedItem().dataSource + self.bigSeekOffset
        self.updateProgress()

    def bigSeekSelected(self):
        self.setFocusId(self.MAIN_BUTTON_ID)
        xbmc.sleep(100)
        self.updateBigSeek()

    def setProperties(self):
        if self.fromSeek:
            self.setFocusId(self.MAIN_BUTTON_ID)
        else:
            self.setFocusId(400)

        if self.handler.playlist:
            if self.handler.playlistPos < len(self.handler.playlist.items()) - 1:
                self.setProperty('has.next', '1')
            else:
                self.setProperty('has.next', '')

            if self.handler.playlistPos > 0:
                self.setProperty('has.prev', '1')
            else:
                self.setProperty('has.prev', '')
        else:
            self.setProperty('has.next', '')
            self.setProperty('has.prev', '')

        self.setProperty('has.bif', self.bifURL and '1' or '')
        self.setProperty('video.title', self.title)
        self.setProperty('video.title2', self.title2)
        self.setProperty('time.duration', util.timeDisplay(self.duration))
        self.updateCurrent()

        div = int(self.duration / 12)
        items = []
        for x in range(12):
            offset = div * x
            items.append(kodigui.ManagedListItem(data_source=offset))
        self.bigSeekControl.reset()
        self.bigSeekControl.addItems(items)

    def updateCurrent(self):
        ratio = self.trueOffset() / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        self.positionControl.setWidth(w)
        to = self.trueOffset()
        self.setProperty('time.current', util.timeDisplay(to))
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
        self.setProperty('time.selection', util.simplifiedTimeDisplay(self.selectedOffset))
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
