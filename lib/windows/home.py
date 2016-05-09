import threading

import xbmc
import xbmcgui

import kodigui
from lib import util
from lib import plex
from lib import backgroundthread
import busy


class SectionHubsTask(backgroundthread.Task):
    def setup(self, sections, callback):
        self.sections = sections
        self.callback = callback
        self.lock = threading.Lock()
        return self

    def moveUpSection(self, section):
        if section not in self.sections:
            return

        self.lock.acquire()
        try:
            if section not in self.sections:  # In case it was removed before the lock was acquired
                return
            self.sections.pop(self.sections.index(section))
            self.sections.insert(0, section)
        finally:
            self.lock.release()

    def run(self):
        while self.sections:
            self.lock.acquire()
            try:
                section = self.sections.pop(0)
            finally:
                self.lock.release()

            if self.isCanceled():
                return

            hubs = plex.PLEX.hubs(section.key, count=10)
            self.callback(section, hubs)


class HomeSection(object):
    key = None
    type = 'home'
    title = 'Home'


class HomeWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-home.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SECTION_LIST_ID = 101
    SERVER_BUTTON_ID = 201
    USER_BUTTON_ID = 202

    HUB_AR16X9_00 = 400
    HUB_POSTER_01 = 401
    HUB_POSTER_02 = 402
    HUB_POSTER_03 = 403
    HUB_POSTER_04 = 404
    HUB_SQUARE_05 = 405
    HUB_AR16X9_06 = 406
    HUB_POSTER_07 = 407
    HUB_POSTER_08 = 408
    HUB_SQUARE_09 = 409
    HUB_SQUARE_10 = 410
    HUB_POSTER_11 = 411
    HUB_POSTER_12 = 412
    HUB_POSTER_13 = 413
    HUB_POSTER_14 = 414
    HUB_AR16X9_15 = 415
    HUB_AR16X9_16 = 416
    HUB_AR16X9_17 = 417

    HUBMAP = {
        # HOME
        'home.continue': {'index': 0, 'with_progress': True, 'with_art': True},
        'home.ondeck': {'index': 1},
        'home.television.recent': {'index': 3},
        'home.movies.recent': {'index': 4},
        'home.music.recent': {'index': 5},
        'home.videos.recent': {'index': 6},
        'home.photos.recent': {'index': 9},
        # SHOW
        'tv.ondeck': {'index': 1},
        'tv.recentlyaired': {'index': 2},
        'tv.recentlyadded': {'index': 3},
        'tv.inprogress': {'index': 4, 'with_progress': True},
        'tv.startwatching': {'index': 7},
        'tv.rediscover': {'index': 8},
        'tv.morefromnetwork': {'index': 11},
        'tv.toprated': {'index': 12},
        'tv.moreingenre': {'index': 13},
        'tv.recentlyviewed': {'index': 14},
        # MOVIE
        'movie.inprogress': {'index': 0, 'with_progress': True, 'with_art': True},
        'movie.recentlyreleased': {'index': 1},
        'movie.recentlyadded': {'index': 2},
        'movie.genre': {'index': 3},
        'movie.director': {'index': 7},
        'movie.actor': {'index': 8},
        'movie.topunwatched': {'index': 11},
        'movie.recentlyviewed': {'index': 12},
        # ARTIST
        'music.recent.added': {'index': 5},
        'music.videos.popular.new': {'index': 6},
        # PHOTO
        'photo.recent': {'index': 5},
        'photo.random.year': {'index': 9},
        'photo.random.decade': {'index': 10},
        # VIDEO
        'video.recent': {'index': 0},
        'video.random.year': {'index': 6},
        'video.random.decade': {'index': 15},
        'video.inprogress': {'index': 16, 'with_progress': True, 'with_art': True},
        'video.unwatched.random': {'index': 17},
    }

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.lastSection = HomeSection
        self.task = None
        self.closeOption = None
        self.hubControls = None
        self.sectionHubs = {}

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)

        self.hubControls = (
            kodigui.ManagedControlList(self, self.HUB_AR16X9_00, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_01, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_02, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_03, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_04, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_05, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_06, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_07, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_08, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_09, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_10, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_11, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_12, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_13, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_14, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_15, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_16, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_17, 5)
        )

        self.bottomItem = 0
        self.serverRefresh()
        self.setFocusId(self.SECTION_LIST_ID)

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOUSE_MOVE):
                self.checkSectionItem()
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.SERVER_BUTTON_ID:
            self.selectServer()
        elif controlID == self.USER_BUTTON_ID:
            self.userOptions()

    def onFocus(self, controlID):
        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID + 100))

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(100).HasFocus(0)'):
            self.setProperty('off.sections', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(100).HasFocus(0)'):
            self.setProperty('off.sections', '1')

    @busy.dialog()
    def serverRefresh(self):
        self.setProperty('hub.focus', '')
        self.displayServerAndUser()
        self.showSections()
        self.showHubs(HomeSection)

    def checkSectionItem(self):
        item = self.sectionList.getSelectedItem()
        if not item:
            return

        if item.getProperty('item'):
            if item.dataSource != self.lastSection:
                self.lastSection = item.dataSource
                self.sectionChanged(item.dataSource)
        else:
            self.sectionList.selectItem(self.bottomItem)

    def displayServerAndUser(self):
        self.setProperty('server.name', plex.PLEX.friendlyName)
        self.setProperty('server.icon', 'script.plex/home/device/plex.png')  # TODO: Set dynamically to whatever it should be if that's how it even works :)
        self.setProperty('server.iconmod', plex.PLEX.isSecure and 'script.plex/home/device/lock.png' or '')
        self.setProperty('user.name', plex.USER.title)
        self.setProperty('user.avatar', plex.USER.thumb)

    def sectionChanged(self, section):
        self.setProperty('hub.focus', '')
        util.DEBUG_LOG('Section chaged: {0}'.format(repr(section.title)))
        self.showHubs(section)

    def sectionHubsCallback(self, section, hubs):
        self.sectionHubs[section.key] = hubs
        if self.lastSection == section:
            self.showHubs(section)

    def showSections(self):
        self.sectionHubs = {}
        items = []

        homemli = kodigui.ManagedListItem('Home', data_source=HomeSection)
        homemli.setProperty('is.home', '1')
        homemli.setProperty('item', '1')
        items.append(homemli)

        sections = plex.PLEX.library.sections()

        self.task = SectionHubsTask().setup([HomeSection] + sections, self.sectionHubsCallback)
        backgroundthread.BGThreader.addTask(self.task)

        for section in sections:
            mli = kodigui.ManagedListItem(section.title, thumbnailImage='script.plex/home/type/{0}.png'.format(section.type), data_source=section)
            mli.setProperty('item', '1')
            items.append(mli)

        self.bottomItem = len(items) - 1

        for x in range(len(items), 8):
            mli = kodigui.ManagedListItem()
            items.append(mli)

        self.lastSection = HomeSection
        self.sectionList.reset()
        self.sectionList.addItems(items)

        self.setFocusId(self.SECTION_LIST_ID)

    def showHubs(self, section=None):
        self.setProperty('drawing', '1')
        try:
            self._showHubs(section=section)
        finally:
            self.setProperty('drawing', '')

    def _showHubs(self, section=None):
        self.clearHubs()

        hubs = self.sectionHubs.get(section.key)
        if not hubs:
            if self.task:
                self.task.moveUpSection(section)
            return

        for hub in hubs:
            if hub.hubIdentifier in self.HUBMAP:
                util.DEBUG_LOG('Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
                self.showHub(hub, **self.HUBMAP[hub.hubIdentifier])
            else:
                util.DEBUG_LOG('UNHANDLED - Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))

    def createGrandparentedListItem(self, obj):
        title = obj.grandparentTitle or obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.thumbUrl, data_source=obj)
        return mli

    def createParentedListItem(self, obj):
        title = obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.thumbUrl, data_source=obj)
        return mli

    def createSimpleListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumbUrl, data_source=obj)
        return mli

    def createListItem(self, obj):
        if obj.type == 'episode':
            return self.createGrandparentedListItem(obj)
        elif obj.type == 'season':
            return self.createParentedListItem(obj)
        elif obj.type == 'movie':
            return self.createSimpleListItem(obj)
        elif obj.type == 'show':
            return self.createSimpleListItem(obj)
        elif obj.type == 'album':
            return self.createParentedListItem(obj)
        elif obj.type == 'track':
            return self.createParentedListItem(obj)
        elif obj.type == 'photo':
            return self.createSimpleListItem(obj)
        elif obj.type == 'clip':
            return self.createSimpleListItem(obj)
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def clearHubs(self):
        for control in self.hubControls:
            control.reset()

    def showHub(self, hub, index=None, with_progress=False, with_art=False):
        if not hub.items:
            return

        self.setProperty('hub.4{0:02d}'.format(index), hub.title)

        control = self.hubControls[index]

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                if with_progress:
                    mli.setProperty('progress', util.getProgressImage(obj))
                if with_art:
                    mli.setThumbnailImage(obj.artUrl)
                items.append(mli)

        control.addItems(items)

    def sectionClicked(self):
        item = self.sectionList.getSelectedItem()
        print item

    def selectServer(self):
        servers = busy.widthDialog(plex.servers, None)

        display = [s.name for s in servers]
        idx = xbmcgui.Dialog().select('Select Server', display)
        if idx < 0:
            return
        server = servers[idx]
        if plex.changeServer(server):
            self.serverRefresh()

    def userOptions(self):
        options = []
        if plex.BASE.multiuser and plex.OWNED:
            options.append(('switch', 'Switch User...'))
        options.append(('signout', 'Sign Out'))

        idx = xbmcgui.Dialog().select('User Options', [o[1] for o in options])
        if idx < 0:
            return

        self.closeOption = options[idx][0]
        self.doClose()

    def finished(self):
        if self.task:
            self.task.cancel()
