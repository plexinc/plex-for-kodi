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

import playlist
import playlists
import posters
import subitems
import episodes
import preplay
import photos
import busy


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
        'home.continue': {'index': 0, 'with_progress': True, 'with_art': True},
        'home.ondeck': {'index': 1},
        'home.television.recent': {'index': 3},
        'home.movies.recent': {'index': 4},
        'home.music.recent': {'index': 5},
        'home.videos.recent': {'index': 6, 'ar16x9': True},
        'home.playlists': {'index': 9},
        'home.photos.recent': {'index': 10},
        # SHOW
        'tv.ondeck': {'index': 1},
        'tv.recentlyaired': {'index': 2},
        'tv.recentlyadded': {'index': 3},
        'tv.inprogress': {'index': 4, 'with_progress': True},
        'tv.startwatching': {'index': 7},
        'tv.rediscover': {'index': 8},
        'tv.morefromnetwork': {'index': 13},
        'tv.toprated': {'index': 14},
        'tv.moreingenre': {'index': 15},
        'tv.recentlyviewed': {'index': 16},
        # MOVIE
        'movie.inprogress': {'index': 0, 'with_progress': True, 'with_art': True},
        'movie.recentlyreleased': {'index': 1},
        'movie.recentlyadded': {'index': 2},
        'movie.genre': {'index': 3},
        'movie.director': {'index': 7},
        'movie.actor': {'index': 8},
        'movie.topunwatched': {'index': 13},
        'movie.recentlyviewed': {'index': 14},
        # ARTIST
        'music.recent.played': {'index': 5},
        'music.recent.added': {'index': 9},
        'music.recent.artist': {'index': 10},
        'music.recent.genre': {'index': 11},
        'music.top.period': {'index': 12},
        'music.popular': {'index': 20},
        'music.recent.label': {'index': 21},
        'music.touring': {'index': 22},
        'music.videos.popular.new': {'index': 18},
        'music.videos.recent.artists': {'index': 19},
        # PHOTO
        'photo.recent': {'index': 5},
        'photo.random.year': {'index': 9},
        'photo.random.decade': {'index': 10},
        'photo.random.dayormonth': {'index': 11},
        # VIDEO
        'video.recent': {'index': 0, 'ar16x9': True},
        'video.random.year': {'index': 6, 'ar16x9': True},
        'video.random.decade': {'index': 17, 'ar16x9': True},
        'video.inprogress': {'index': 18, 'with_progress': True, 'ar16x9': True},
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
        self.sectionHubs = {}

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

    def onFocus(self, controlID):
        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(self.hubFocusIndexes[controlID - 400]))

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(100).HasFocus(0)'):
            self.setProperty('off.sections', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(100).HasFocus(0)'):
            self.setProperty('off.sections', '1')

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

        if mli.dataSource.TYPE in ('episode', 'movie'):
            self.playableClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('show'):
            self.showClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('artist'):
            self.artistClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('season'):
            self.seasonClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('album'):
            self.albumClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('photo'):
            self.photoClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('photodirectory'):
            self.photoDirectoryClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('playlist'):
            self.playlistClicked(mli.dataSource)
        elif mli.dataSource.TYPE in ('clip'):
            player.PLAYER.playVideo(mli.dataSource)

    def playableClicked(self, playable):
        w = preplay.PrePlayWindow.open(video=playable)
        del w

    def showClicked(self, show):
        w = subitems.ShowWindow.open(media_item=show)
        del w

    def artistClicked(self, artist):
        w = subitems.ArtistWindow.open(media_item=artist)
        del w

    def seasonClicked(self, season):
        w = episodes.EpisodesWindow.open(season=season)
        del w

    def albumClicked(self, album):
        w = episodes.AlbumWindow.open(season=album)
        del w

    def photoClicked(self, photo):
        w = photos.PhotoWindow.open(photo=photo)
        del w

    def photoDirectoryClicked(self, photodirectory):
        w = posters.SquaresWindow.open(section=photodirectory)
        del w

    def playlistClicked(self, pl):
        w = playlist.PlaylistWindow.open(playlist=pl)
        del w

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

        pl = plexapp.SERVERMANAGER.selectedServer.playlists()
        if pl:
            # util.TEST(pl[0].composite.asTranscodedImageURL(640, 360))
            plli = kodigui.ManagedListItem('Playlists', thumbnailImage='script.plex/home/type/playlists.png', data_source=PlaylistsSection)
            plli.setProperty('is.plaulists', '1')
            plli.setProperty('item', '1')
            items.append(plli)

        sections = plexapp.SERVERMANAGER.selectedServer.library.sections()

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

        self.setFocusId(self.SECTION_LIST_ID)

    def showHubs(self, section=None):
        self.setProperty('drawing', '1')
        try:
            self._showHubs(section=section)
        finally:
            self.setProperty('drawing', '')

    def _showHubs(self, section=None):
        self.clearHubs()

        if section.key is False:
            self.showBusy(False)
            return

        self.showBusy(True)

        hubs = self.sectionHubs.get(section.key)
        if not hubs:
            # if self.task:
            #     self.task.moveUpSection(section)
            return

        try:
            for hub in hubs:
                if hub.hubIdentifier in self.HUBMAP:
                    util.DEBUG_LOG('Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
                    self.showHub(hub, **self.HUBMAP[hub.hubIdentifier])
                else:
                    util.DEBUG_LOG('UNHANDLED - Hub: {0} ({1})'.format(hub.hubIdentifier, len(hub.items)))
        finally:
            self.showBusy(False)

    def createGrandparentedListItem(self, obj, thumb_w, thumb_h, with_grandparent_title=False):
        if with_grandparent_title and obj.grandparentTitle and obj.title:
            title = u'{0} - {1}'.format(obj.grandparentTitle, obj.title)
        else:
            title = obj.grandparentTitle or obj.parentTitle or obj.title or ''
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

    def createListItem(self, obj):
        if obj.type == 'episode':
            mli = self.createGrandparentedListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
            return mli
        elif obj.type == 'season':
            mli = self.createParentedListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
            return mli
        elif obj.type == 'movie':
            mli = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
            return mli
        elif obj.type == 'show':
            mli = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
            return mli
        elif obj.type == 'album':
            mli = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM, with_parent_title=True)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        elif obj.type == 'track':
            mli = self.createGrandparentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        elif obj.type in ('photo', 'photodirectory'):
            mli = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
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

    def showHub(self, hub, index=None, with_progress=False, with_art=False, ar16x9=False):
        if not hub.items:
            return

        self.setProperty('hub.4{0:02d}'.format(index), hub.title)

        control = self.hubControls[index]

        items = []

        for obj in hub.items:
            if not self.backgroundSet:
                self.backgroundSet = True
                self.setProperty(
                    'background', obj.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
                )
            mli = self.createListItem(obj)
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

        control.addItems(items)

    def sectionClicked(self):
        item = self.sectionList.getSelectedItem()
        if not item:
            return

        section = item.dataSource

        if section.type in ('show', 'movie'):
            posters.PostersWindow.open(section=section)
        elif section.type in ('artist', 'photo'):
            posters.SquaresWindow.open(section=section)
        elif section.type in ('playlists',):
            playlists.PlaylistsWindow.open()

    def showServers(self):
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

        self.serverList.reset()
        self.serverList.addItems(items)

        self.getControl(800).setHeight((min(len(items), 9) * 100) + 80)

        self.setFocusId(self.SERVER_LIST_ID)

    def selectServer(self):
        mli = self.serverList.getSelectedItem()
        if not mli:
            return

        server = mli.dataSource
        self.setFocusId(self.SERVER_BUTTON_ID)

        if plexapp.SERVERMANAGER.setSelectedServer(server, force=True):
            self.serverRefresh()

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
        w = musicplayer.MusicPlayerWindow.open()
        del w

    def finished(self):
        if self.tasks:
            for task in self.tasks:
                task.cancel()
