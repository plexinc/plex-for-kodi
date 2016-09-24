import xbmcgui

import kodigui
import busy

from lib import util
from plexnet import plexapp, plexplayer, playqueue


class PhotoWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-photo.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    PREV_BUTTON_ID = 404
    NEXT_BUTTON_ID = 409

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.photo = kwargs.get('photo')
        self.playQueue = None
        self.playerObject = None
        self.timelineType = 'photo'
        self.lastTimelineState = None
        self.ignoreTimelines = False
        self.trueTime = 0

    def onFirstInit(self):
        self.getPlayQueue()
        self.start()

    def onAction(self, action):
        try:
            # controlID = self.getFocusId()
            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.PREV_BUTTON_ID:
            self.prev()
        elif controlID == self.NEXT_BUTTON_ID:
            self.next()

    def getPlayQueue(self, shuffle=False):
        if True:
            self.playQueue = playqueue.createPlayQueueForItem(self.photo, options={'shuffle': shuffle})
            util.DEBUG_LOG('waiting for playQueue to initialize')
            if busy.widthDialog(self.playQueue.waitForInitialization, None):
                util.DEBUG_LOG('playQueue initialized: {0}'.format(self.playQueue))
            else:
                util.DEBUG_LOG('playQueue timed out wating for initialization')

    def showPhoto(self, photo):
        if not photo:
            return

        self.playerObject = plexplayer.PlexPhotoPlayer(photo)
        meta = self.playerObject.build()
        self.setProperty('photo', meta.get('url', ''))
        self.updateNowPlaying(force=True, refreshQueue=True)

    def start(self):
        self.showPhoto(self.playQueue.current())

    def prev(self):
        self.showPhoto(self.playQueue.prev())

    def next(self):
        self.showPhoto(self.playQueue.next())

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
