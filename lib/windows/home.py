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

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.lastSection = HomeSection
        self.task = None
        self.closeOption = None
        self.sectionHubs = {}

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)

        self.hub_AR16x9_00 = kodigui.ManagedControlList(self, self.HUB_AR16X9_00, 5)
        self.hub_POSTER_01 = kodigui.ManagedControlList(self, self.HUB_POSTER_01, 5)
        self.hub_POSTER_02 = kodigui.ManagedControlList(self, self.HUB_POSTER_02, 5)
        self.hub_POSTER_03 = kodigui.ManagedControlList(self, self.HUB_POSTER_03, 5)
        self.hub_POSTER_04 = kodigui.ManagedControlList(self, self.HUB_POSTER_04, 5)
        self.hub_SQUARE_05 = kodigui.ManagedControlList(self, self.HUB_SQUARE_05, 5)
        self.hub_AR16x9_06 = kodigui.ManagedControlList(self, self.HUB_AR16X9_06, 5)
        self.hub_POSTER_07 = kodigui.ManagedControlList(self, self.HUB_POSTER_07, 5)
        self.hub_POSTER_08 = kodigui.ManagedControlList(self, self.HUB_POSTER_08, 5)
        self.hub_SQUARE_09 = kodigui.ManagedControlList(self, self.HUB_SQUARE_09, 5)
        self.hub_SQUARE_10 = kodigui.ManagedControlList(self, self.HUB_SQUARE_10, 5)
        self.hub_POSTER_11 = kodigui.ManagedControlList(self, self.HUB_POSTER_11, 5)
        self.hub_POSTER_12 = kodigui.ManagedControlList(self, self.HUB_POSTER_12, 5)
        self.hub_POSTER_13 = kodigui.ManagedControlList(self, self.HUB_POSTER_13, 5)
        self.hub_POSTER_14 = kodigui.ManagedControlList(self, self.HUB_POSTER_14, 5)

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
        self.clearHubs()

        hubs = self.sectionHubs.get(section.key)
        if not hubs:
            if self.task:
                self.task.moveUpSection(section)
            return

        if section.type == 'show':
            return self.showShowHubs(hubs)
        elif section.type == 'artist':
            return self.showMusicHubs(hubs)
        elif section.type == 'photo':
            return self.showPhotoHubs(hubs)

        for hub in hubs:
            util.DEBUG_LOG('Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
            if hub.hubIdentifier in ('home.continue', 'movie.inprogress'):
                self.showHub_AR16x9_00(hub)
            elif hub.hubIdentifier == 'home.ondeck':
                self.showHub_POSTER_01(hub)
            elif hub.hubIdentifier == 'home.television.recent':
                self.showHub_POSTER_03(hub)
            elif hub.hubIdentifier in ('home.movies.recent', 'movie.recentlyadded'):
                self.showHub_POSTER_04(hub)
            elif hub.hubIdentifier == 'home.music.recent':
                self.showHub_SQUARE_05(hub)
            elif hub.hubIdentifier in ('home.videos.recent', 'video.recent'):
                self.showHub_AR16x9_06(hub)

    def showShowHubs(self, hubs):
        for hub in hubs:
            util.DEBUG_LOG('Hub (Show): {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))

            if hub.hubIdentifier == 'tv.ondeck':
                self.showHub_POSTER_01(hub)
            elif hub.hubIdentifier == 'tv.recentlyaired':
                self.showHub_POSTER_02(hub)
            elif hub.hubIdentifier == 'tv.recentlyadded':
                self.showHub_POSTER_03(hub)
            elif hub.hubIdentifier == 'tv.inprogress':
                self.showHub_POSTER_04(hub, with_progress=True)
            elif hub.hubIdentifier == 'tv.startwatching':
                self.showHub_POSTER_07(hub)
            elif hub.hubIdentifier == 'tv.rediscover':
                self.showHub_POSTER_08(hub)
            elif hub.hubIdentifier == 'tv.morefromnetwork':
                self.showHub_POSTER_11(hub)
            elif hub.hubIdentifier == 'tv.toprated':
                self.showHub_POSTER_12(hub)
            elif hub.hubIdentifier == 'tv.moreingenre':
                self.showHub_POSTER_13(hub)
            elif hub.hubIdentifier == 'tv.recentlyviewed':
                self.showHub_POSTER_14(hub)

    def showMusicHubs(self, hubs):
        for hub in hubs:
            util.DEBUG_LOG('Hub (Music): {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))

            if hub.hubIdentifier == 'music.recent.added':
                self.showHub_SQUARE_05(hub)
            elif hub.hubIdentifier == 'music.videos.popular.new':
                self.showHub_AR16x9_06(hub)

    def showPhotoHubs(self, hubs):
        for hub in hubs:
            util.DEBUG_LOG('Hub (Photo): {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))

            if hub.hubIdentifier == 'photo.recent':
                self.showHub_SQUARE_05(hub)
            elif hub.hubIdentifier == 'photo.random.year':
                self.showHub_SQUARE_09(hub)
            elif hub.hubIdentifier == 'photo.random.decade':
                self.showHub_SQUARE_10(hub)

    def createEpisodeListItem(self, ep):
        mli = kodigui.ManagedListItem(ep.grandparentTitle, thumbnailImage=ep.thumbUrl, data_source=ep)
        prog = util.getProgressImage(ep)
        if prog:
            mli.setProperty('progress', prog)

        return mli

    def createSeasonListItem(self, season):
        mli = kodigui.ManagedListItem(season.parentTitle, thumbnailImage=season.thumbUrl, data_source=season)
        return mli

    def createMovieListItem(self, movie):
        mli = kodigui.ManagedListItem(movie.title, thumbnailImage=movie.thumbUrl, data_source=movie)
        return mli

    def createShowListItem(self, show):
        mli = kodigui.ManagedListItem(show.title, thumbnailImage=show.thumbUrl, data_source=show)
        return mli

    def createAlbumListItem(self, album):
        mli = kodigui.ManagedListItem(album.title, thumbnailImage=album.thumbUrl, data_source=album)
        return mli

    def createClipListItem(self, clip):
        mli = kodigui.ManagedListItem(clip.title, thumbnailImage=clip.thumbUrl, data_source=clip)
        return mli

    def createListItem(self, obj):
        if obj.type == 'episode':
            return self.createEpisodeListItem(obj)
        elif obj.type == 'season':
            return self.createSeasonListItem(obj)
        elif obj.type == 'movie':
            return self.createMovieListItem(obj)
        elif obj.type == 'show':
            return self.createShowListItem(obj)
        elif obj.type == 'album':
            return self.createSeasonListItem(obj)
        elif obj.type == 'track':
            return self.createSeasonListItem(obj)
        elif obj.type == 'photo':
            return self.createShowListItem(obj)
        elif obj.type == 'clip':
            return self.createClipListItem(obj)
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def clearHubs(self):
        self.hub_AR16x9_00.reset()
        self.hub_POSTER_01.reset()
        self.hub_POSTER_02.reset()
        self.hub_POSTER_03.reset()
        self.hub_POSTER_04.reset()
        self.hub_SQUARE_05.reset()
        self.hub_AR16x9_06.reset()
        self.hub_POSTER_07.reset()
        self.hub_POSTER_08.reset()
        self.hub_SQUARE_09.reset()
        self.hub_SQUARE_10.reset()
        self.hub_POSTER_11.reset()
        self.hub_POSTER_12.reset()
        self.hub_POSTER_13.reset()
        self.hub_POSTER_14.reset()

    def showHub(self, control, hub, with_progress=False):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                if with_progress:
                    mli.setProperty('progress', util.getProgressImage(obj))
                items.append(mli)

        control.addItems(items)

    def showHub_AR16x9_00(self, hub):
        if not hub.items:
            return

        self.setProperty('hub.400', hub.title)

        mitems = []
        for hitem in hub.items:
            mli = kodigui.ManagedListItem(hitem.title, thumbnailImage=hitem.artUrl, data_source=hitem)
            mli.setProperty('progress', util.getProgressImage(hitem))
            mitems.append(mli)

        self.hub_AR16x9_00.addItems(mitems)

    def showHub_POSTER_01(self, hub, with_progress=False):
        self.setProperty('hub.401', hub.title)
        return self.showHub(self.hub_POSTER_01, hub, with_progress)

    def showHub_POSTER_02(self, hub, with_progress=False):
        self.setProperty('hub.402', hub.title)
        return self.showHub(self.hub_POSTER_02, hub, with_progress)

    def showHub_POSTER_03(self, hub, with_progress=False):
        self.setProperty('hub.403', hub.title)
        return self.showHub(self.hub_POSTER_03, hub, with_progress)

    def showHub_POSTER_04(self, hub, with_progress=False):
        self.setProperty('hub.404', hub.title)
        return self.showHub(self.hub_POSTER_04, hub, with_progress)

    def showHub_SQUARE_05(self, hub):
        self.setProperty('hub.405', hub.title)
        return self.showHub(self.hub_SQUARE_05, hub)

    def showHub_AR16x9_06(self, hub):
        self.setProperty('hub.406', hub.title)
        return self.showHub(self.hub_AR16x9_06, hub)

    def showHub_POSTER_07(self, hub, with_progress=False):
        self.setProperty('hub.407', hub.title)
        return self.showHub(self.hub_POSTER_07, hub, with_progress)

    def showHub_POSTER_08(self, hub, with_progress=False):
        self.setProperty('hub.408', hub.title)
        return self.showHub(self.hub_POSTER_08, hub, with_progress)

    def showHub_SQUARE_09(self, hub):
        self.setProperty('hub.409', hub.title)
        self.showHub(self.hub_SQUARE_09, hub)

    def showHub_SQUARE_10(self, hub):
        self.setProperty('hub.410', hub.title)
        self.showHub(self.hub_SQUARE_10, hub)

    def showHub_POSTER_11(self, hub, with_progress=False):
        self.setProperty('hub.411', hub.title)
        return self.showHub(self.hub_POSTER_11, hub, with_progress)

    def showHub_POSTER_12(self, hub, with_progress=False):
        self.setProperty('hub.412', hub.title)
        return self.showHub(self.hub_POSTER_12, hub, with_progress)

    def showHub_POSTER_13(self, hub, with_progress=False):
        self.setProperty('hub.413', hub.title)
        return self.showHub(self.hub_POSTER_13, hub, with_progress)

    def showHub_POSTER_14(self, hub, with_progress=False):
        self.setProperty('hub.414', hub.title)
        return self.showHub(self.hub_POSTER_14, hub, with_progress)

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
        plex.changeServer(server)
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
