import xbmc
import xbmcgui
import kodigui
from lib import util
from lib import plex
from lib import compat


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

    CONTINUE_WATCHING_LIST_ID = 300

    ONDECK1_LIST_ID = 400
    ONDECK2_LIST_ID = 401

    RA_TV1_LIST_ID = 402
    RA_TV2_LIST_ID = 403

    RA_MOVIES1_LIST_ID = 404
    RA_MOVIES2_LIST_ID = 405

    PANEL_1WIDE_WIDTH = 251
    PANEL_2WIDE_WIDTH = 479

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)
        self.continueWatchingList = kodigui.ManagedControlList(self, self.CONTINUE_WATCHING_LIST_ID, 3)
        self.onDeck1List = kodigui.ManagedControlList(self, self.ONDECK1_LIST_ID, 1)
        self.onDeck2List = kodigui.ManagedControlList(self, self.ONDECK2_LIST_ID, 4)
        self.raTV1List = kodigui.ManagedControlList(self, self.RA_TV1_LIST_ID, 1)
        self.raTV2List = kodigui.ManagedControlList(self, self.RA_TV2_LIST_ID, 4)
        self.raMovies1List = kodigui.ManagedControlList(self, self.RA_MOVIES1_LIST_ID, 1)
        self.raMovies2List = kodigui.ManagedControlList(self, self.RA_MOVIES2_LIST_ID, 4)

        self.bottomItem = 0
        self.serverRefresh()
        self.setFocusId(self.SECTION_LIST_ID)

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
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
        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        if xbmc.getCondVisibility('ControlGroup(150).HasFocus(0)'):
            self.setProperty('on.library', '1')
        elif xbmc.getCondVisibility('ControlGroup(100).HasFocus(0)'):
            self.setProperty('on.library', '')

    def serverRefresh(self):
        self.setProperty('busy', '1')
        try:
            self.displayServerAndUser()
            self.showSections()
            self.showLibrary()
        finally:
            self.setProperty('busy', '')

    def checkSectionItem(self):
        item = self.sectionList.getSelectedItem()
        if not item.getProperty('item'):
            self.sectionList.selectItem(self.bottomItem)

    def displayServerAndUser(self):
        self.setProperty('server.name', plex.PLEX.friendlyName)
        self.setProperty('server.icon', 'script.plex/home/device/plex.png')  # TODO: Set dynamically to whatever it should be if that's how it even works :)
        self.setProperty('server.iconmod', 'script.plex/home/device/lock.png')
        self.setProperty('user.name', plex.USER.title)
        self.setProperty('user.avatar', plex.USER.thumb)

    def showSections(self):
        items = []

        sections = plex.PLEX.library.sections()
        for section in sections:
            mli = kodigui.ManagedListItem(section.title, thumbnailImage='script.plex/home/type/{0}.png'.format(section.type), data_source=section)
            mli.setProperty('item', '1')
            items.append(mli)

        self.bottomItem = len(items) - 1

        for x in range(len(items), 7):
            mli = kodigui.ManagedListItem()
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    def showLibrary(self):
        self.clearOnDeck()
        self.clearRecentlyAdded()
        self.showOnDeck()
        self.showRecentlyAdded()

    def clearOnDeck(self):
        self.onDeck1List.reset()
        self.onDeck2List.reset()

    def showOnDeck(self):
        ondeck = plex.PLEX.library.onDeck()
        if not ondeck:
            return

        now = compat.datetime.datetime.now()

        movies = [
            m for m in ondeck if m.type == 'movie' and (hasattr(m, 'lastViewedAt') and compat.timedelta_total_seconds(now - m.lastViewedAt) <= 604800)
        ]

        self.continueWatchingList.reset()

        if movies:
            mitems = []
            for movie in movies[:3]:
                mli = kodigui.ManagedListItem(movie.title, thumbnailImage=movie.artUrl, data_source=movie)
                mli.setProperty('progress', util.getProgressImage(movie))
                print mli.getProperty('progress')
                mitems.append(mli)

            if mitems:
                mitems[0].setProperty('header', 'CONTINUE WATCHING')

            self.continueWatchingList.addItems(mitems)

        episodes = [e for e in ondeck if e.type == 'episode']

        if episodes:
            episodes = episodes * 5
            eitems = []
            for ep in episodes[:5]:
                mli = kodigui.ManagedListItem(thumbnailImage=ep.thumbUrl, data_source=ep)
                eitems.append(mli)

            if eitems:
                eitems[0].setProperty('header', 'ON DECK')

            self.onDeck1List.addItems(eitems[0:1])
            self.onDeck2List.addItems(eitems[1:5])

            if len(eitems) < 4:
                self.onDeck2List.setWidth(self.PANEL_1WIDE_WIDTH)
            else:
                self.onDeck2List.setWidth(self.PANEL_2WIDE_WIDTH)

    def clearRecentlyAdded(self):
        self.raTV1List.reset()
        self.raTV2List.reset()
        self.raMovies1List.reset()
        self.raMovies2List.reset()

    def showRecentlyAdded(self):
        ra = plex.PLEX.library.recentlyAdded()
        if not ra:
            return

        IDs = {}

        seasons = [s for s in ra if s.type == 'season']
        movies = [m for m in ra if m.type == 'movie']

        if seasons:
            sitems = []
            for i, season in enumerate(seasons):
                if i > 4:
                    break
                show = season.show()
                ID = show.guid
                if ID not in IDs:
                    IDs[ID] = 1
                    mli = kodigui.ManagedListItem(thumbnailImage=show.thumbUrl, data_source=season)
                    sitems.append(mli)
                    i += 1

            if sitems:
                sitems[0].setProperty('header', 'RECENTLY ADDED TELEVISION')

            self.raTV1List.addItems(sitems[0:1])
            self.raTV2List.addItems(sitems[1:5])

            if len(sitems) < 4:
                self.raTV2List.setWidth(self.PANEL_1WIDE_WIDTH)
            else:
                self.raTV2List.setWidth(self.PANEL_2WIDE_WIDTH)

        if movies:
            mitems = []
            for movie in movies[0:5]:
                mli = kodigui.ManagedListItem(thumbnailImage=movie.thumbUrl, data_source=movie)
                mitems.append(mli)

            if mitems:
                mitems[0].setProperty('header', 'RECENTLY ADDED MOVIES')

            self.raMovies1List.addItems(mitems[0:1])
            self.raMovies2List.addItems(mitems[1:5])

            if len(mitems) < 4:
                self.raMovies2List.setWidth(self.PANEL_1WIDE_WIDTH)
            else:
                self.raMovies2List.setWidth(self.PANEL_2WIDE_WIDTH)

    def sectionClicked(self):
        item = self.sectionList.getSelectedItem()
        print item.dataSource

    def selectServer(self):
        self.setProperty('busy', '1')
        try:
            servers = plex.servers()
        finally:
            self.setProperty('busy', '')

        display = [s.name for s in servers]
        idx = xbmcgui.Dialog().select('Select Server', display)
        if idx < 0:
            return
        server = servers[idx]
        plex.changeServer(server)
        self.serverRefresh()

    def userOptions(self):
        pass
