import xbmc
import xbmcgui
import kodigui
from lib import util
from lib import plex
import busy


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

    ONDECK_GROUP_ID = 500
    ONDECK1_LIST_ID = 400
    ONDECK2_LIST_ID = 401

    ONDECK_MORE_BUTTON_GROUP_ID = 481

    RA_TV_GROUP_ID = 501
    RA_TV1_LIST_ID = 402
    RA_TV2_LIST_ID = 403

    RA_TV_MORE_BUTTON_GROUP_ID = 483

    RA_MOVIES_GROUP_ID = 502
    RA_MOVIES1_LIST_ID = 404
    RA_MOVIES2_LIST_ID = 405

    RA_MOVIES_MORE_BUTTON_GROUP_ID = 485

    GROUP_1WIDE_WIDTH = 495
    GROUP_2WIDE_WIDTH = 723
    GROUP_3WIDE_WIDTH = 951

    PANEL_1WIDE_WIDTH = 251
    PANEL_2WIDE_WIDTH = 479

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)
        self.continueWatchingList = kodigui.ManagedControlList(self, self.CONTINUE_WATCHING_LIST_ID, 3)

        self.onDeckGroup = self.getControl(self.ONDECK_GROUP_ID)
        self.raTVGroup = self.getControl(self.RA_TV_GROUP_ID)
        self.raMoviesGroup = self.getControl(self.RA_MOVIES_GROUP_ID)

        self.onDeckMoreButtonGroup = self.getControl(self.ONDECK_MORE_BUTTON_GROUP_ID)
        self.raTVMoreButtonGroup = self.getControl(self.RA_TV_MORE_BUTTON_GROUP_ID)
        self.raMoviesMoreButtonGroup = self.getControl(self.RA_MOVIES_MORE_BUTTON_GROUP_ID)

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

    @busy.dialog()
    def serverRefresh(self):
        self.displayServerAndUser()
        self.showSections()
        self.showHubs()

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

    def showHubs(self):
        self.clearOnDeck()
        self.clearRecentlyAdded()
        hubs = plex.PLEX.hubs()
        for hub in hubs:
            if hub.hubIdentifier == 'home.continue':
                self.showContinue(hub)
            elif hub.hubIdentifier == 'home.ondeck':
                self.showOnDeck(hub)
            elif hub.hubIdentifier == 'home.television.recent':
                self.showTVRecent(hub)
            elif hub.hubIdentifier == 'home.movies.recent':
                self.showMoviesRecent(hub)

    def createEpisodeListItem(self, ep):
        footer = u'S{0} \u2022 E{1}'.format(ep.parentIndex, ep.index)
        # Set descriptive Label for Kodi Screen Reader - not dislayed
        label = u'Show: {0} Episode: {1} - {2}'.format(ep.grandparentTitle, footer, ep.title)
        mli = kodigui.ManagedListItem(label, footer, thumbnailImage=ep.thumbUrl, data_source=ep)
        mli.setProperty('footer1', ep.grandparentTitle)
        mli.setProperty(
            'footer2', '{0} / {1} / {2}'.format(
                ep.title,
                ep.originallyAvailableAt.strftime('%B %d, %Y').replace(' 0', ' '),  # Cheap day leading zero remove
                util.durationToShortText(ep.duration)
            )
        )
        prog = util.getProgressImage(ep)
        if prog:
            mli.setProperty('progress', prog)
        elif not ep.isWatched:
            mli.setProperty('unwatched', '1')

        return mli

    def createSeasonListItem(self, season):
        mli = kodigui.ManagedListItem(thumbnailImage=season.thumbUrl, data_source=season)
        mli.setProperty('footer1', season.parentTitle)
        mli.setProperty('footer2', season.title)
        mli.setProperty('leaf.count', str(season.leafCount))
        return mli

    def createMovieListItem(self, movie):
        mli = kodigui.ManagedListItem(thumbnailImage=movie.thumbUrl, data_source=movie)
        mli.setProperty('footer1', movie.title)
        mli.setProperty('footer2', '{0} / {1}'.format(movie.year, util.durationToShortText(movie.duration)))
        if not movie.isWatched:
            mli.setProperty('unwatched', '1')
        return mli

    def createShowListItem(self, show):
        mli = kodigui.ManagedListItem(thumbnailImage=show.thumbUrl, data_source=show)
        mli.setProperty('footer1', show.title)
        mli.setProperty('footer2', util.durationToShortText(show.duration))
        mli.setProperty('leaf.count', str(show.leafCount))
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
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def clearOnDeck(self):
        self.continueWatchingList.reset()
        self.onDeck1List.reset()
        self.onDeck2List.reset()

    def showContinue(self, hub):
        if not hub.items:
            return

        mitems = []
        for movie in hub.items[:3]:
            mli = kodigui.ManagedListItem(movie.title, thumbnailImage=movie.artUrl, data_source=movie)
            mli.setProperty('progress', util.getProgressImage(movie))
            mli.setProperty('footer1', movie.title)
            mli.setProperty('footer2', '{0} / {1}'.format(movie.year, util.durationToShortText(movie.duration)))
            mitems.append(mli)

        self.continueWatchingList.addItems(mitems)

    def showOnDeck(self, hub):
        if not hub.items:
            return

        self.onDeckMoreButtonGroup.setVisible(hub.more)

        items = []
        for obj in hub.items[:5]:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        # if eitems:
        #     eitems[0].setProperty('header', 'ON DECK')

        self.onDeck1List.addItems(items[0:1])
        self.onDeck2List.addItems(items[1:5])
        if len(items) < 2:
            self.onDeckGroup.setWidth(self.GROUP_1WIDE_WIDTH)
        elif len(items) < 4:
            self.onDeckGroup.setWidth(self.GROUP_2WIDE_WIDTH)
            self.onDeck2List.setWidth(self.PANEL_1WIDE_WIDTH)
        else:
            self.onDeckGroup.setWidth(self.GROUP_3WIDE_WIDTH)
            self.onDeck2List.setWidth(self.PANEL_2WIDE_WIDTH)

    def clearRecentlyAdded(self):
        self.raTV1List.reset()
        self.raTV2List.reset()
        self.raMovies1List.reset()
        self.raMovies2List.reset()

    def showTVRecent(self, hub):
        if not hub.items:
            return

        self.raTVMoreButtonGroup.setVisible(hub.more)

        items = []
        for obj in hub.items[:5]:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.raTV1List.addItems(items[0:1])
        self.raTV2List.addItems(items[1:5])

        if len(items) < 2:
            self.raTVGroup.setWidth(self.GROUP_1WIDE_WIDTH)
        elif len(items) < 4:
            self.raTVGroup.setWidth(self.GROUP_2WIDE_WIDTH)
            self.raTV2List.setWidth(self.PANEL_1WIDE_WIDTH)
        else:
            self.raTVGroup.setWidth(self.GROUP_3WIDE_WIDTH)
            self.raTV2List.setWidth(self.PANEL_2WIDE_WIDTH)

    def showMoviesRecent(self, hub):
        if not hub.items:
            return

        self.raMoviesMoreButtonGroup.setVisible(hub.more and True or False)

        items = []
        for obj in hub.items[0:5]:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

        self.raMovies1List.addItems(items[0:1])
        self.raMovies2List.addItems(items[1:5])

        if len(items) < 2:
            self.raMoviesGroup.setWidth(self.GROUP_1WIDE_WIDTH)
        elif len(items) < 4:
            self.raMoviesGroup.setWidth(self.GROUP_2WIDE_WIDTH)
            self.raMovies2List.setWidth(self.PANEL_1WIDE_WIDTH)
        else:
            self.raMoviesGroup.setWidth(self.GROUP_3WIDE_WIDTH)
            self.raMovies2List.setWidth(self.PANEL_2WIDE_WIDTH)

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
