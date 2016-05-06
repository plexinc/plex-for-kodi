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

    CONTINUE_WATCHING_LIST_ID = 400
    ONDECK_LIST_ID = 401
    RAIRED_TV_LIST_ID = 402
    RA_TV_LIST_ID = 403
    RA_MOVIES_LIST_ID = 404
    RA_MUSIC_LIST_ID = 405
    RA_VIDEOS_LIST_ID = 406
    CONTINUE_WATCHING_TV_LIST_ID = 407
    START_WATCHING_TV_LIST_ID = 408

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.lastSection = HomeSection
        self.task = None
        self.closeOption = None
        self.sectionHubs = {}

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)
        self.continueWatchingList = kodigui.ManagedControlList(self, self.CONTINUE_WATCHING_LIST_ID, 5)

        self.onDeckList = kodigui.ManagedControlList(self, self.ONDECK_LIST_ID, 5)
        self.rAiredTVList = kodigui.ManagedControlList(self, self.RAIRED_TV_LIST_ID, 5)
        self.raTVList = kodigui.ManagedControlList(self, self.RA_TV_LIST_ID, 5)
        self.raMoviesList = kodigui.ManagedControlList(self, self.RA_MOVIES_LIST_ID, 5)
        self.raMusicList = kodigui.ManagedControlList(self, self.RA_MUSIC_LIST_ID, 5)
        self.raVideosList = kodigui.ManagedControlList(self, self.RA_VIDEOS_LIST_ID, 5)

        self.cwTVList = kodigui.ManagedControlList(self, self.CONTINUE_WATCHING_TV_LIST_ID, 5)

        self.swTVList = kodigui.ManagedControlList(self, self.START_WATCHING_TV_LIST_ID, 5)

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

        for hub in hubs:
            util.DEBUG_LOG('Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
            if hub.hubIdentifier in ('home.continue', 'movie.inprogress'):
                self.showContinue(hub)
            elif hub.hubIdentifier in ('home.ondeck', 'tv.ondeck'):
                self.showOnDeck(hub)
            elif hub.hubIdentifier in ('home.television.recent', 'tv.recentlyadded'):
                self.showTVRecent(hub)
            elif hub.hubIdentifier in ('home.movies.recent', 'movie.recentlyadded'):
                self.showMoviesRecent(hub)
            elif hub.hubIdentifier in ('home.music.recent', 'music.recent.added'):
                self.showMusicRecent(hub)
            elif hub.hubIdentifier in ('home.videos.recent', 'video.recent'):
                self.showVideosRecent(hub)
            elif hub.hubIdentifier in ('tv.recentlyaired',):
                self.showTVRecentAired(hub)
            elif hub.hubIdentifier in ('tv.inprogress',):
                self.showTVContinue(hub)
            elif hub.hubIdentifier in ('tv.startwatching',):
                self.showTVStartWatching(hub)

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
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def clearHubs(self):
        self.continueWatchingList.reset()
        self.onDeckList.reset()
        self.rAiredTVList.reset()
        self.raTVList.reset()
        self.raMoviesList.reset()
        self.raMusicList.reset()
        self.raVideosList.reset()
        self.cwTVList.reset()
        self.swTVList.reset()

    def showHub(self, control, hub):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        control.addItems(items)

    def showContinue(self, hub):
        if not hub.items:
            return

        mitems = []
        for movie in hub.items:
            mli = kodigui.ManagedListItem(movie.title, thumbnailImage=movie.artUrl, data_source=movie)
            mli.setProperty('progress', util.getProgressImage(movie))
            mitems.append(mli)

        self.continueWatchingList.addItems(mitems)

    def showTVContinue(self, hub):
        if not hub.items:
            return

        sitems = []
        for show in hub.items:
            mli = kodigui.ManagedListItem(show.title, thumbnailImage=show.thumbUrl, data_source=show)
            mli.setProperty('progress', util.getProgressImage(show))
            sitems.append(mli)

        self.cwTVList.addItems(sitems)

    def showOnDeck(self, hub):
        self.showHub(self.onDeckList, hub)

    def showTVRecentAired(self, hub):
        return self.showHub(self.rAiredTVList, hub)

    def showTVRecent(self, hub):
        return self.showHub(self.raTVList, hub)

    def showMoviesRecent(self, hub):
        return self.showHub(self.raMoviesList, hub)

    def showMusicRecent(self, hub):
        return self.showHub(self.raMusicList, hub)

    def showVideosRecent(self, hub):
        self.showHub(self.raVideosList, hub)

    def showTVStartWatching(self, hub):
        return self.showHub(self.swTVList, hub)

    def sectionClicked(self):
        item = self.sectionList.getSelectedItem()
        print item.dataSource

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
