import threading
import time

import xbmc
import xbmcgui

import kodigui
import busy

from lib import util, colors
from plexnet import plexapp, plexplayer, playqueue


class PhotoWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-photo.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OVERLAY_BUTTON_ID = 250
    OSD_GROUP_ID = 200

    OSD_BUTTONS_GROUP_ID = 400
    REPEAT_BUTTON_ID = 401
    SHUFFLE_BUTTON_ID = 402
    PREV_BUTTON_ID = 404
    PLAY_PAUSE_BUTTON_ID = 406
    STOP_BUTTON_ID = 407
    NEXT_BUTTON_ID = 409
    PQUEUE_BUTTON_ID = 412

    PQUEUE_LIST_ID = 500
    PQUEUE_LIST_OVERLAY_BUTTON_ID = 501

    SLIDESHOW_INTERVAL = 3

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.photo = kwargs.get('photo')
        self.playQueue = None
        self.playerObject = None
        self.timelineType = 'photo'
        self.lastTimelineState = None
        self.ignoreTimelines = False
        self.trueTime = 0
        self.slideshowThread = None
        self.slideshowRunning = False
        self.slideshowNext = 0
        self.osdTimer = None
        self.lastItem = None
        self.showPhotoThread = None
        self.showPhotoTimeout = 0

    def onFirstInit(self):
        self.pqueueList = kodigui.ManagedControlList(self, self.PQUEUE_LIST_ID, 14)
        self.getPlayQueue()
        self.start()
        self.osdTimer = kodigui.PropertyTimer(self._winID, 4, 'OSD', '', callback=self.osdTimerCallback)

    def osdTimerCallback(self):
        self.setFocusId(self.OVERLAY_BUTTON_ID)

    def onAction(self, action):
        try:
            # controlID = self.getFocusId()
            if action == xbmcgui.ACTION_MOVE_LEFT:
                if not self.osdVisible() or self.getFocusId() == self.PQUEUE_LIST_OVERLAY_BUTTON_ID:
                    self.prev()
            elif action == xbmcgui.ACTION_MOVE_RIGHT:
                if not self.osdVisible() or self.getFocusId() == self.PQUEUE_LIST_OVERLAY_BUTTON_ID:
                    self.next()
            elif action == xbmcgui.ACTION_MOVE_UP:
                if self.osdVisible():
                    if self.getFocusId() == self.OVERLAY_BUTTON_ID:
                        self.hideOSD()
                    else:
                        self.showOSD()
            elif action == xbmcgui.ACTION_MOVE_DOWN:
                if self.osdVisible():
                    if self.getFocusId() == self.OVERLAY_BUTTON_ID:
                        self.hideOSD()
                    else:
                        self.showOSD()
            elif action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                if self.osdVisible():
                    self.hideOSD()
                    return
                self.doClose()
                return

            self.osdTimer.reset()
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def checkPqueueListChanged(self):
        item = self.pqueueList.getSelectedItem()
        if item == self.lastItem:
            return

        self.lastItem = item
        self.onPqueueListChanged()

    def onClick(self, controlID):
        if controlID == self.PREV_BUTTON_ID:
            self.prev()
        elif controlID == self.NEXT_BUTTON_ID:
            self.next()
        elif controlID == self.PLAY_PAUSE_BUTTON_ID:
            if self.getProperty('playing'):
                self.pause()
            else:
                self.play()
        elif controlID == self.STOP_BUTTON_ID:
            self.stop()
        elif controlID == self.OVERLAY_BUTTON_ID:
            self.showOSD()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.REPEAT_BUTTON_ID:
            self.repeatButtonClicked()

    def shuffleButtonClicked(self):
        self.playQueue.setShuffle()

    def repeatButtonClicked(self):
        if self.playQueue.isRepeat:
            self.playQueue.setRepeat(False)
            self.playQueue.refresh(force=True)
        else:
            self.playQueue.setRepeat(True)
            self.playQueue.refresh(force=True)

    def getPlayQueue(self, shuffle=False):
        self.playQueue = playqueue.createPlayQueueForItem(self.photo, options={'shuffle': shuffle})
        self.playQueue.on('items.changed', self.fillPqueueList)
        self.playQueue.on('change', self.updateProperties)

        util.DEBUG_LOG('waiting for playQueue to initialize')
        if busy.widthDialog(self.playQueue.waitForInitialization, None):
            util.DEBUG_LOG('playQueue initialized: {0}'.format(self.playQueue))
        else:
            util.DEBUG_LOG('playQueue timed out wating for initialization')
        self.showPhoto()

    def fillPqueueList(self, **kwargs):
        items = []
        for qi in self.playQueue.items():
            mli = kodigui.ManagedListItem(thumbnailImage=qi.thumb.asTranscodedImageURL(123, 123), data_source=qi)
            items.append(mli)

        self.pqueueList.replaceItems(items)
        self.updatePqueueListSelection()

    def updatePqueueListSelection(self, current=None):
        selected = self.pqueueList.getListItemByDataSource(current or self.playQueue.current())
        if not selected:
            return

        self.pqueueList.selectItem(selected.pos())

    def showPhoto(self, **kwargs):
        self.slideshowNext = 0

        photo = self.playQueue.current()
        self.updatePqueueListSelection(photo)

        self.showPhotoTimeout = time.time() + 0.2
        if not self.showPhotoThread or not self.showPhotoThread.isAlive():
            self.showPhotoThread = threading.Thread(target=self._showPhoto, name="showphoto")
            self.showPhotoThread.start()

    def _showPhoto(self):
        monitor = xbmc.Monitor()
        while not monitor.waitForAbort(0.1):
            if time.time() >= self.showPhotoTimeout:
                break

        self._reallyShowPhoto()

    @busy.dialog()
    def _reallyShowPhoto(self):
        photo = self.playQueue.current()
        self.playerObject = plexplayer.PlexPhotoPlayer(photo)
        meta = self.playerObject.build()
        self.setProperty('photo', meta.get('url', ''))
        self.setProperty('background', photo.thumb.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))

        self.updateNowPlaying(force=True, refreshQueue=True)
        self.resetNext()

    def updateProperties(self, **kwargs):
        self.setProperty('pq.shuffled', self.playQueue.isShuffled and '1' or '')
        self.setProperty('pq.repeat', self.playQueue.isRepeat and '1' or '')
        if not self.getProperty('hide.prev') and not self.playQueue.hasPrev():
            if self.playQueue.hasNext():
                self.setFocusId(self.NEXT_BUTTON_ID)
            else:
                self.setFocusId(self.PLAY_PAUSE_BUTTON_ID)
        self.setProperty('hide.prev', not self.playQueue.hasPrev() and '1' or '')
        if not self.getProperty('hide.next') and not self.playQueue.hasNext():
            if self.playQueue.hasPrev():
                self.setFocusId(self.PREV_BUTTON_ID)
            else:
                self.setFocusId(self.PLAY_PAUSE_BUTTON_ID)
        self.setProperty('hide.next', not self.playQueue.hasNext() and '1' or '')

    def slideshow(self):
        util.DEBUG_LOG('Slideshow: STARTED')
        self.slideshowRunning = True
        monitor = xbmc.Monitor()

        self.resetNext()
        while not monitor.waitForAbort(0.1) and self.slideshowRunning:
            if not self.slideshowNext or time.time() < self.slideshowNext:
                continue
            util.TEST(time.time())
            self.next()

        util.DEBUG_LOG('Slideshow: STOPPED')

    def resetNext(self):
        self.slideshowNext = time.time() + self.SLIDESHOW_INTERVAL

    def osdVisible(self):
        return self.getProperty('OSD')

    def pqueueVisible(self):
        return self.getProperty('show.pqueue')

    def start(self):
        self.setFocusId(self.OVERLAY_BUTTON_ID)

    def prev(self):
        self.playQueue.prev()
        self.updateProperties()
        self.showPhoto()

    def next(self):
        self.playQueue.next()
        self.updateProperties()
        self.showPhoto()

    def play(self):
        self.setProperty('playing', '1')
        if self.slideshowThread and self.slideshowThread.isAlive():
            return

        self.slideshowThread = threading.Thread(target=self.slideshow, name='slideshow')
        self.slideshowThread.start()

    def pause(self):
        self.setProperty('playing', '')
        self.slideshowRunning = False

    def stop(self):
        self.doClose()

    def doClose(self):
        self.pause()
        kodigui.BaseWindow.doClose(self)

    def getCurrentItem(self):
        if self.playerObject:
            return self.playerObject.item
        return None

    def shouldSendTimeline(self, item):
        return item.ratingKey and item.getServer()

    def updateNowPlaying(self, force=False, refreshQueue=False, state=None):
        if self.ignoreTimelines:
            return

        item = self.getCurrentItem()

        if not item:
            return

        if not self.shouldSendTimeline(item):
            return

        state = state or 'paused'
        # Avoid duplicates
        if state == self.lastTimelineState and not force:
            return

        self.lastTimelineState = state
        # self.timelineTimer.reset()

        time = int(self.trueTime * 1000)

        # self.trigger("progress", [m, item, time])

        if refreshQueue and self.playQueue:
            self.playQueue.refreshOnTimeline = True

        plexapp.APP.nowplayingmanager.updatePlaybackState(self.timelineType, self.playerObject, state, time, self.playQueue)

    def showOSD(self):
        self.osdTimer.reset()

    def hideOSD(self):
        self.osdTimer.stop(trigger=True)
