import time
import threading

import xbmc
import xbmcgui

import kodigui
from lib import util
from lib import backgroundthread
from lib import colors
from lib import player

import plexnet
from plexnet import plexapp

import playlists
import posters
import busy
import opener
import search


class SectionHubsTask(backgroundthread.Task):
    def setup(self, section, callback):
        self.section = section
        self.callback = callback
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
            return

        try:
            hubs = plexapp.SERVERMANAGER.selectedServer.hubs(self.section.key, count=10)
            if self.isCanceled():
                return
            self.callback(self.section, hubs)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on section: {0}'.format(repr(self.section.title)))


class UpdateHubTask(backgroundthread.Task):
    def setup(self, hub, callback):
        self.hub = hub
        self.callback = callback
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
            return

        try:
            self.hub.reload()
            if self.isCanceled():
                return
            self.callback(self.hub)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on section: {0}'.format(repr(self.section.title)))


class HomeSection(object):
    key = None
    type = 'home'
    title = 'Home'


class PlaylistsSection(object):
    key = False
    type = 'playlists'
    title = 'Playlists'


class HomeWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-home.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_GROUP_ID = 200

    SECTION_LIST_ID = 101
    SERVER_BUTTON_ID = 201

    USER_BUTTON_ID = 202
    USER_LIST_ID = 250

    SEARCH_BUTTON_ID = 203
    SERVER_LIST_ID = 260

    PLAYER_STATUS_BUTTON_ID = 204

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
    HUB_SQUARE_11 = 411
    HUB_SQUARE_12 = 412
    HUB_POSTER_13 = 413
    HUB_POSTER_14 = 414
    HUB_POSTER_15 = 415
    HUB_POSTER_16 = 416
    HUB_AR16X9_17 = 417
    HUB_AR16X9_18 = 418
    HUB_AR16X9_19 = 419

    HUB_SQUARE_20 = 420
    HUB_SQUARE_21 = 421
    HUB_SQUARE_22 = 422

    HUB_AR16X9_23 = 423

    HUBMAP = {
        # HOME
        'home.continue': {'index': 0, 'with_progress': True, 'with_art': True, 'do_updates': True, 'text2lines': True},
        'home.ondeck': {'index': 1, 'do_updates': True, 'text2lines': True},
        'home.television.recent': {'index': 2, 'text2lines': True, 'text2lines': True},
        'home.movies.recent': {'index': 4, 'text2lines': True},
        'home.music.recent': {'index': 5, 'text2lines': True},
        'home.videos.recent': {'index': 6, 'ar16x9': True},
        'home.playlists': {'index': 9},
        'home.photos.recent': {'index': 10, 'text2lines': True},
        # SHOW
        'tv.ondeck': {'index': 1, 'do_updates': True, 'text2lines': True},
        'tv.recentlyaired': {'index': 2, 'text2lines': True},
        'tv.recentlyadded': {'index': 3, 'text2lines': True},
        'tv.inprogress': {'index': 4, 'with_progress': True, 'do_updates': True, 'text2lines': True},
        'tv.startwatching': {'index': 7},
        'tv.rediscover': {'index': 8},
        'tv.morefromnetwork': {'index': 13},
        'tv.toprated': {'index': 14},
        'tv.moreingenre': {'index': 15},
        'tv.recentlyviewed': {'index': 16, 'text2lines': True},
        # MOVIE
        'movie.inprogress': {'index': 0, 'with_progress': True, 'with_art': True, 'do_updates': True, 'text2lines': True},
        'movie.recentlyreleased': {'index': 1, 'text2lines': True},
        'movie.recentlyadded': {'index': 2, 'text2lines': True},
        'movie.genre': {'index': 3, 'text2lines': True},
        'movie.director': {'index': 7, 'text2lines': True},
        'movie.actor': {'index': 8, 'text2lines': True},
        'movie.topunwatched': {'index': 13, 'text2lines': True},
        'movie.recentlyviewed': {'index': 14, 'text2lines': True},
        # ARTIST
        'music.recent.played': {'index': 5, 'do_updates': True},
        'music.recent.added': {'index': 9, 'text2lines': True},
        'music.recent.artist': {'index': 10, 'text2lines': True},
        'music.recent.genre': {'index': 11, 'text2lines': True},
        'music.top.period': {'index': 12, 'text2lines': True},
        'music.popular': {'index': 20, 'text2lines': True},
        'music.recent.label': {'index': 21, 'text2lines': True},
        'music.touring': {'index': 22},
        'music.videos.popular.new': {'index': 18},
        'music.videos.recent.artists': {'index': 19},
        # PHOTO
        'photo.recent': {'index': 5, 'text2lines': True},
        'photo.random.year': {'index': 9, 'text2lines': True},
        'photo.random.decade': {'index': 10, 'text2lines': True},
        'photo.random.dayormonth': {'index': 11, 'text2lines': True},
        # VIDEO
        'video.recent': {'index': 0, 'ar16x9': True},
        'video.random.year': {'index': 6, 'ar16x9': True},
        'video.random.decade': {'index': 17, 'ar16x9': True},
        'video.inprogress': {'index': 18, 'with_progress': True, 'ar16x9': True, 'do_updates': True},
        'video.unwatched.random': {'index': 19, 'ar16x9': True},
        'video.recentlyviewed': {'index': 23, 'ar16x9': True},
    }

    THUMB_POSTER_DIM = (287, 425)
    THUMB_AR16X9_DIM = (619, 348)
    THUMB_SQUARE_DIM = (425, 425)

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.lastSection = HomeSection
        self.tasks = None
        self.closeOption = None
        self.hubControls = None
        self.backgroundSet = False
        self.sectionChangeThread = None
        self.sectionChangeTimeout = 0
        self.sectionHubs = {}
        self.updateHubs = {}

    def onFirstInit(self):
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 7)
        self.serverList = kodigui.ManagedControlList(self, self.SERVER_LIST_ID, 10)
        self.userList = kodigui.ManagedControlList(self, self.USER_LIST_ID, 3)

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
            kodigui.ManagedControlList(self, self.HUB_SQUARE_11, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_12, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_13, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_14, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_15, 5),
            kodigui.ManagedControlList(self, self.HUB_POSTER_16, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_17, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_18, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_19, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_20, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_21, 5),
            kodigui.ManagedControlList(self, self.HUB_SQUARE_22, 5),
            kodigui.ManagedControlList(self, self.HUB_AR16X9_23, 5),
        )

        self.hubFocusIndexes = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 17, 18, 19, 20, 21, 22, 13, 14, 15, 23)

        self.bottomItem = 0
        if self.serverRefresh():
            self.setFocusId(self.SECTION_LIST_ID)

        plexapp.SERVERMANAGER.on('new:server', self.onNewServer)
        plexapp.SERVERMANAGER.on('remove:server', self.onRemoveServer)
        plexapp.SERVERMANAGER.on('reachable:server', self.onReachableServer)

        plexapp.APP.on('change:selectedServer', self.onSelectedServerChange)

        player.PLAYER.on('session.ended', self.updateOnDeckHubs)
        util.MONITOR.on('changed.watchstatus', self.updateOnDeckHubs)

    def onAction(self, action):
        controlID = self.getFocusId()

        try:
            if controlID == self.SERVER_BUTTON_ID and action == xbmcgui.ACTION_MOVE_RIGHT:
                self.setFocusId(self.USER_BUTTON_ID)
            elif controlID == self.USER_BUTTON_ID and action == xbmcgui.ACTION_MOVE_LEFT:
                self.setFocusId(self.SERVER_BUTTON_ID)
            elif controlID == self.SEARCH_BUTTON_ID and action == xbmcgui.ACTION_MOVE_RIGHT:
                if xbmc.getCondVisibility('Player.HasMedia + Control.IsVisible({0})'.format(self.PLAYER_STATUS_BUTTON_ID)):
                    self.setFocusId(self.PLAYER_STATUS_BUTTON_ID)
                else:
                    self.setFocusId(self.SERVER_BUTTON_ID)
            elif controlID == self.PLAYER_STATUS_BUTTON_ID and action == xbmcgui.ACTION_MOVE_RIGHT:
                self.setFocusId(self.SERVER_BUTTON_ID)
            if controlID == self.SECTION_LIST_ID:
                self.checkSectionItem()
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return

            if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                if self.getFocusId() == self.USER_LIST_ID:
                    self.setFocusId(self.USER_BUTTON_ID)
                    return
                elif self.getFocusId() == self.SERVER_LIST_ID:
                    self.setFocusId(self.SERVER_BUTTON_ID)
                    return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.SERVER_BUTTON_ID:
            self.showServers()
        elif controlID == self.SERVER_LIST_ID:
            self.selectServer()
        elif controlID == self.USER_BUTTON_ID:
            self.showUserMenu()
        elif controlID == self.USER_LIST_ID:
            self.doUserOption()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif 399 < controlID < 500:
            self.hubItemClicked(controlID)
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def onFocus(self, controlID):
        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(self.hubFocusIndexes[controlID - 400]))

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(100).HasFocus(0)'):
            self.setProperty('off.sections', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(100).HasFocus(0)'):
            self.setProperty('off.sections', '1')

    def searchButtonClicked(self):
        search.dialog()

    def updateOnDeckHubs(self, **kwargs):
        tasks = [UpdateHubTask().setup(hub, self.updateHubCallback) for hub in self.updateHubs.values()]
        self.tasks += tasks
        backgroundthread.BGThreader.addTasks(tasks)

    def showBusy(self, on=True):
        self.setProperty('busy', on and '1' or '')

    @busy.dialog()
    def serverRefresh(self):
        backgroundthread.BGThreader.reset()
        if self.tasks:
            for task in self.tasks:
                task.cancel()

        self.setProperty('hub.focus', '')
        self.displayServerAndUser()
        if not plexapp.SERVERMANAGER.selectedServer:
            self.setFocusId(self.USER_BUTTON_ID)
            return False

        self.showSections()
        self.backgroundSet = False
        self.showHubs(HomeSection)
        return True

    def hubItemClicked(self, hubControlID):
        control = self.hubControls[hubControlID - 400]
        mli = control.getSelectedItem()
        if not mli:
            return

        self.processCommand(opener.open(mli.dataSource))

    def processCommand(self, command):
        if command.startswith('HOME:'):
            sectionID = command.split(':', 1)[-1]
            for mli in self.sectionList:
                if mli.dataSource and mli.dataSource.key == sectionID:
                    self.sectionList.selectItem(mli.pos())
                    self.lastSection = mli.dataSource
                    self.sectionChanged(mli.dataSource)

    def checkSectionItem(self):
        item = self.sectionList.getSelectedItem()
        if not item:
            return

        if not item.getProperty('item'):
            self.sectionList.selectItem(self.bottomItem)
            item = self.sectionList[self.bottomItem]

        if item.dataSource != self.lastSection:
            self.lastSection = item.dataSource
            self.sectionChanged(item.dataSource)

    def displayServerAndUser(self):
        self.setProperty('user.name', plexapp.ACCOUNT.title or plexapp.ACCOUNT.username)
        self.setProperty('user.avatar', plexapp.ACCOUNT.thumb)

        if plexapp.SERVERMANAGER.selectedServer:
            self.setProperty('server.name', plexapp.SERVERMANAGER.selectedServer.name)
            self.setProperty('server.icon', 'script.plex/home/device/plex.png')  # TODO: Set dynamically to whatever it should be if that's how it even works :)
            self.setProperty('server.iconmod', plexapp.SERVERMANAGER.selectedServer.isSecure and 'script.plex/home/device/lock.png' or '')
        else:
            self.setProperty('server.name', 'No Servers Found')
            self.setProperty('server.icon', 'script.plex/home/device/error.png')
            self.setProperty('server.iconmod', '')

    def sectionChanged(self, section):
        self.sectionChangeTimeout = time.time() + 0.3
        if not self.sectionChangeThread or not self.sectionChangeThread.isAlive():
            self.sectionChangeThread = threading.Thread(target=self._sectionChanged, name="sectionchanged")
            self.sectionChangeThread.start()

    def _sectionChanged(self):
        while not util.MONITOR.waitForAbort(0.1):
            if time.time() >= self.sectionChangeTimeout:
                break

        self._sectionReallyChanged()

    def _sectionReallyChanged(self):
        section = self.lastSection
        self.setProperty('hub.focus', '')
        util.DEBUG_LOG('Section chaged ({0}): {1}'.format(section.key, repr(section.title)))
        self.showHubs(section)

    def sectionHubsCallback(self, section, hubs):
        self.sectionHubs[section.key] = hubs
        if self.lastSection == section:
            self.showHubs(section)

    def updateHubCallback(self, hub):
        for mli in self.sectionList:
            section = mli.dataSource
            if not section:
                continue

            hubs = self.sectionHubs.get(section.key, ())
            for idx, ihub in enumerate(hubs):
                if ihub == hub:
                    if self.lastSection == section:
                        util.DEBUG_LOG('Hub {0} updated - refreshing section: {1}'.format(hub.hubIdentifier, repr(section.title)))
                        hubs[idx] = hub
                        self.showHub(hub)
                        return

    def showSections(self):
        self.sectionHubs = {}
        items = []

        homemli = kodigui.ManagedListItem('Home', data_source=HomeSection)
        homemli.setProperty('is.home', '1')
        homemli.setProperty('item', '1')
        items.append(homemli)

        pl = plexapp.SERVERMANAGER.selectedServer.playlists()
        if pl:
            plli = kodigui.ManagedListItem('Playlists', thumbnailImage='script.plex/home/type/playlists.png', data_source=PlaylistsSection)
            plli.setProperty('is.playlists', '1')
            plli.setProperty('item', '1')
            items.append(plli)

        sections = plexapp.SERVERMANAGER.selectedServer.library.sections()

        if plexapp.SERVERMANAGER.selectedServer.hasHubs():
            self.tasks = [SectionHubsTask().setup(s, self.sectionHubsCallback) for s in [HomeSection] + sections]
            backgroundthread.BGThreader.addTasks(self.tasks)

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

        if items:
            self.setFocusId(self.SECTION_LIST_ID)
        else:
            self.setFocusId(self.SERVER_BUTTON_ID)

    def showHubs(self, section=None):
        self.setProperty('drawing', '1')
        try:
            self._showHubs(section=section)
        finally:
            self.setProperty('drawing', '')

    def _showHubs(self, section=None):
        self.clearHubs()

        if not plexapp.SERVERMANAGER.selectedServer.hasHubs():
            return

        if section.key is False:
            self.showBusy(False)
            return

        self.showBusy(True)

        hubs = self.sectionHubs.get(section.key)
        if not hubs:
            for task in self.tasks:
                if task.section == section:
                    backgroundthread.BGThreader.moveToFront(task)
                    break
            return

        try:
            for hub in hubs:
                if self.showHub(hub):
                    if self.HUBMAP[hub.hubIdentifier].get('do_updates'):
                        self.updateHubs[hub.hubIdentifier] = hub
        finally:
            self.showBusy(False)

    def showHub(self, hub):
        if hub.hubIdentifier in self.HUBMAP:
            util.DEBUG_LOG('Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
            self._showHub(hub, **self.HUBMAP[hub.hubIdentifier])
            return True
        else:
            util.DEBUG_LOG('UNHANDLED - Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
            return

    def createGrandparentedListItem(self, obj, thumb_w, thumb_h, with_grandparent_title=False):
        if with_grandparent_title and obj.get('grandparentTitle') and obj.title:
            title = u'{0} - {1}'.format(obj.grandparentTitle, obj.title)
        else:
            title = obj.get('grandparentTitle') or obj.get('parentTitle') or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createParentedListItem(self, obj, thumb_w, thumb_h, with_parent_title=False):
        if with_parent_title and obj.parentTitle and obj.title:
            title = u'{0} - {1}'.format(obj.parentTitle, obj.title)
        else:
            title = obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createSimpleListItem(self, obj, thumb_w, thumb_h):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createListItem(self, obj, wide=False):
        if obj.type == 'episode':
            mli = self.createGrandparentedListItem(obj, *self.THUMB_POSTER_DIM)
            if wide:
                mli.setLabel2(u'{0} - S{1} \u2022 E{2}'.format(util.shortenText(obj.title, 35), obj.parentIndex, obj.index))
            else:
                mli.setLabel2(u'S{0} \u2022 E{1}'.format(obj.parentIndex, obj.index))
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
            return mli
        elif obj.type == 'season':
            mli = self.createParentedListItem(obj, *self.THUMB_POSTER_DIM)
            # mli.setLabel2('Season {0}'.format(obj.index))
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
            return mli
        elif obj.type == 'movie':
            mli = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setLabel2(obj.year)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
            return mli
        elif obj.type == 'show':
            mli = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
            return mli
        elif obj.type == 'album':
            mli = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setLabel2(obj.title)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        elif obj.type == 'track':
            mli = self.createGrandparentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setLabel2(obj.title)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        elif obj.type in ('photo', 'photodirectory'):
            mli = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
            if obj.type == 'photo':
                mli.setLabel2(obj.originallyAvailableAt.asDatetime('%d %B %Y'))
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
            return mli
        elif obj.type == 'clip':
            mli = self.createGrandparentedListItem(obj, *self.THUMB_AR16X9_DIM, with_grandparent_title=True)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie16x9.png')
            return mli
        elif obj.type in ('artist', 'playlist'):
            mli = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def clearHubs(self):
        for control in self.hubControls:
            control.reset()

    def _showHub(self, hub, index=None, with_progress=False, with_art=False, ar16x9=False, text2lines=False, **kwargs):
        if not hub.items:
            return

        self.setProperty('hub.4{0:02d}'.format(index), hub.title)
        self.setProperty('hub.text2lines.4{0:02d}'.format(index), text2lines and '1' or '')

        control = self.hubControls[index]

        items = []

        for obj in hub.items:
            if not self.backgroundSet:
                self.backgroundSet = True
                self.setProperty(
                    'background', obj.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
                )
            mli = self.createListItem(obj, wide=with_art)
            if mli:
                items.append(mli)

        if with_progress:
            for mli in items:
                mli.setProperty('progress', util.getProgressImage(mli.dataSource))
        if with_art:
            for mli in items:
                mli.setThumbnailImage(mli.dataSource.art.asTranscodedImageURL(*self.THUMB_AR16X9_DIM))
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie16x9.png')
        if ar16x9:
            for mli in items:
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie16x9.png')

        control.replaceItems(items)

    def sectionClicked(self):
        item = self.sectionList.getSelectedItem()
        if not item:
            return

        section = item.dataSource

        if section.type in ('show', 'movie'):
            self.processCommand(opener.handleOpen(posters.PostersWindow, section=section))
        elif section.type in ('artist', 'photo'):
            self.processCommand(opener.handleOpen(posters.SquaresWindow, section=section))
        elif section.type in ('playlists',):
            self.processCommand(opener.handleOpen(playlists.PlaylistsWindow))

    def onNewServer(self, **kwargs):
        self.showServers(from_refresh=True)

    def onRemoveServer(self, **kwargs):
        self.onNewServer()

    def onReachableServer(self, server=None, **kwargs):
        for mli in self.serverList:
            if mli.dataSource == server:
                return
        else:
            self.onNewServer()

    def onSelectedServerChange(self, **kwargs):
        if self.serverRefresh():
            self.setFocusId(self.SECTION_LIST_ID)

    def showServers(self, from_refresh=False):
        selection = None
        if from_refresh:
            mli = self.serverList.getSelectedItem()
            if mli:
                selection = mli.dataSource
        else:
            plexapp.refreshResources()

        servers = sorted(
            [s for s in plexapp.SERVERMANAGER.getServers() if s.isReachable()],
            key=lambda x: (x.owned and '0' or '1') + x.name.lower()
        )

        items = []
        for s in servers:
            item = kodigui.ManagedListItem(s.name, not s.owned and s.owner or '', data_source=s)
            item.setProperty('secure', s.isSecure and '1' or '')
            item.setProperty('current', plexapp.SERVERMANAGER.selectedServer == s and '1' or '')
            items.append(item)

        if len(items) > 1:
            items[0].setProperty('first', '1')
            items[-1].setProperty('last', '1')
        elif items:
            items[0].setProperty('only', '1')

        self.serverList.replaceItems(items)

        self.getControl(800).setHeight((min(len(items), 9) * 100) + 80)

        if selection:
            for mli in self.serverList:
                if mli.dataSource == selection:
                    self.serverList.selectItem(mli.pos())

        if not from_refresh and items:
            self.setFocusId(self.SERVER_LIST_ID)

    def selectServer(self):
        mli = self.serverList.getSelectedItem()
        if not mli:
            return

        server = mli.dataSource
        self.setFocusId(self.SERVER_BUTTON_ID)

        plexapp.SERVERMANAGER.setSelectedServer(server, force=True)

    def showUserMenu(self):
        items = []
        if len(plexapp.ACCOUNT.homeUsers) > 1:
            items.append(kodigui.ManagedListItem('Switch User', data_source='switch'))
        items.append(kodigui.ManagedListItem('Settings', data_source='settings'))
        items.append(kodigui.ManagedListItem('Sign Out', data_source='signout'))

        if len(items) > 1:
            items[0].setProperty('first', '1')
            items[-1].setProperty('last', '1')
        else:
            items[0].setProperty('only', '1')

        self.userList.reset()
        self.userList.addItems(items)

        self.getControl(801).setHeight((len(items) * 66) + 80)

        self.setFocusId(self.USER_LIST_ID)

    def doUserOption(self):
        mli = self.userList.getSelectedItem()
        if not mli:
            return

        option = mli.dataSource

        self.setFocusId(self.USER_BUTTON_ID)

        if option == 'settings':
            import settings
            settings.SettingsWindow.open()
        else:
            self.closeOption = option
            self.doClose()

    def showAudioPlayer(self):
        import musicplayer
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow))

    def finished(self):
        if self.tasks:
            for task in self.tasks:
                task.cancel()
