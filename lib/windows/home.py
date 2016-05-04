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
        return self

    def run(self):
        for section in [None] + self.sections:
            if self.isCanceled():
                return

            hubs = plex.PLEX.hubs(section and section.key or None)
            self.callback(section, hubs)


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
    RA_TV_LIST_ID = 402
    RA_MOVIES_LIST_ID = 403
    RA_MUSIC_LIST_ID = 404
    RA_VIDEOS_LIST_ID = 405

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.lastSection = None
        self.task = None
        self.sectionHubs = {}

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)
        self.continueWatchingList = kodigui.ManagedControlList(self, self.CONTINUE_WATCHING_LIST_ID, 5)

        self.onDeckList = kodigui.ManagedControlList(self, self.ONDECK_LIST_ID, 5)
        self.raTVList = kodigui.ManagedControlList(self, self.RA_TV_LIST_ID, 5)
        self.raMoviesList = kodigui.ManagedControlList(self, self.RA_MOVIES_LIST_ID, 5)
        self.raMusicList = kodigui.ManagedControlList(self, self.RA_MUSIC_LIST_ID, 5)
        self.raVideosList = kodigui.ManagedControlList(self, self.RA_VIDEOS_LIST_ID, 5)

        self.bottomItem = 0
        self.serverRefresh()
        self.setFocusId(self.SECTION_LIST_ID)

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
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
        print controlID

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
        self.showHubs()

    def checkSectionItem(self):
        item = self.sectionList.getSelectedItem()
        if item.getProperty('item'):
            if item.dataSource != self.lastSection:
                self.lastSection = item.dataSource
                self.sectionChanged(item.dataSource)
        else:
            self.sectionList.selectItem(self.bottomItem)

    def displayServerAndUser(self):
        self.setProperty('server.name', plex.PLEX.friendlyName)
        self.setProperty('server.icon', 'script.plex/home/device/plex.png')  # TODO: Set dynamically to whatever it should be if that's how it even works :)
        self.setProperty('server.iconmod', 'script.plex/home/device/lock.png')
        self.setProperty('user.name', plex.USER.title)
        self.setProperty('user.avatar', plex.USER.thumb)

    def sectionChanged(self, section):
        self.setProperty('hub.focus', '')
        if section:
            util.DEBUG_LOG('Section chaged: {0}'.format(repr(section.title)))
            self.showHubs(section=section.key)
        else:
            util.DEBUG_LOG('Section chaged: Home')
            self.showHubs()

    def sectionHubsCallback(self, section, hubs):
        self.sectionHubs[section and section.key or None] = hubs
        if self.lastSection == section:
            self.showHubs(section and section.key or None)

    def showSections(self):
        self.sectionHubs = {}
        items = []

        homemli = kodigui.ManagedListItem('Home')
        homemli.setProperty('is.home', '1')
        homemli.setProperty('item', '1')
        items.append(homemli)

        sections = plex.PLEX.library.sections()

        self.task = SectionHubsTask().setup(sections, self.sectionHubsCallback)
        backgroundthread.BGThreader.addTask(self.task)

        for section in sections:
            mli = kodigui.ManagedListItem(section.title, thumbnailImage='script.plex/home/type/{0}.png'.format(section.type), data_source=section)
            mli.setProperty('item', '1')
            items.append(mli)

        self.bottomItem = len(items) - 1

        for x in range(len(items), 8):
            mli = kodigui.ManagedListItem()
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    def showHubs(self, section=None):
        self.clearOnDeck()
        self.clearRecentlyAdded()

        hubs = self.sectionHubs.get(section, [])

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
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def clearOnDeck(self):
        self.continueWatchingList.reset()
        self.onDeckList.reset()

    def showContinue(self, hub):
        if not hub.items:
            return

        mitems = []
        for movie in hub.items:
            mli = kodigui.ManagedListItem(movie.title, thumbnailImage=movie.artUrl, data_source=movie)
            mli.setProperty('progress', util.getProgressImage(movie))
            mitems.append(mli)

        self.continueWatchingList.addItems(mitems)

    def showOnDeck(self, hub):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.onDeckList.addItems(items)

    def clearRecentlyAdded(self):
        self.raTVList.reset()
        self.raMoviesList.reset()
        self.raMusicList.reset()
        self.raVideosList.reset()

    def showTVRecent(self, hub):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.raTVList.addItems(items)

    def showMoviesRecent(self, hub):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.raMoviesList.addItems(items)

    def showMusicRecent(self, hub):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.raMusicList.addItems(items)

    def showVideosRecent(self, hub):
        if not hub.items:
            return

        items = []
        for obj in hub.items:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.raVideosList.addItems(items)

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
        pass

    def finished(self):
        if self.task:
            self.task.cancel()
