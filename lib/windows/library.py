import os
import random
import urllib
import json
import threading

import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util
from lib import backgroundthread

import busy
import subitems
import preplay
import search
import plexnet
import dropdown
import opener
import windowutils

from plexnet import playqueue

from lib.util import T


KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

MOVE_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_MOVE_UP,
        xbmcgui.ACTION_MOVE_DOWN,
        xbmcgui.ACTION_MOUSE_MOVE,
        xbmcgui.ACTION_PAGE_UP,
        xbmcgui.ACTION_PAGE_DOWN,
        xbmcgui.ACTION_FIRST_PAGE,
        xbmcgui.ACTION_LAST_PAGE,
        xbmcgui.ACTION_MOUSE_WHEEL_DOWN,
        xbmcgui.ACTION_MOUSE_WHEEL_UP
    )
)

THUMB_POSTER_DIM = (268, 397)
THUMB_AR16X9_DIM = (619, 348)
THUMB_SQUARE_DIM = (355, 355)
ART_AR16X9_DIM = (630, 355)

TYPE_KEYS = {
    'episode': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM,
    },
    'season': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM
    },
    'movie': {
        'fallback': 'movie',
        'thumb_dim': THUMB_POSTER_DIM,
        'art_dim': ART_AR16X9_DIM
    },
    'show': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM,
        'art_dim': ART_AR16X9_DIM
    },
    'album': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'artist': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'track': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'photo': {
        'fallback': 'photo',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'clip': {
        'fallback': 'movie16x9',
        'thumb_dim': THUMB_POSTER_DIM
    },
}

TYPE_PLURAL = {
    'artist': T(32347, 'artists'),
    'movie': T(32348, 'movies'),
    'photo': T(32349, 'photos'),
    'show': T(32350, 'shows')
}

SORT_KEYS = {
    'movie': {
        'addedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added')},
        'originallyAvailableAt': {'title': T(32353, 'By Release Date'), 'display': T(32354, 'Release Date')},
        'lastViewedAt': {'title': T(32355, 'By Date Viewed'), 'display': T(32356, 'Date Viewed')},
        'titleSort': {'title': T(32357, 'By Name'), 'display': T(32358, 'Name')},
        'rating': {'title': T(32359, 'By Rating'), 'display': T(32360, 'Rating')},
        'resolution': {'title': T(32361, 'By Resolution'), 'display': T(32362, 'Resolution')},
        'duration': {'title': T(32363, 'By Duration'), 'display': T(32364, 'Duration')},
        'unwatched': {'title': T(32367, 'By Unwatched'), 'display': T(32368, 'Unwatched')},
        'viewCount': {'title': T(32371, 'By Play Count'), 'display': T(32372, 'Play Count')}
    },
    'show': {
        'originallyAvailableAt': {'title': T(32365, 'By First Aired'), 'display': T(32366, 'First Aired')},
        'unviewedLeafCount': {'title': T(32367, 'By Unwatched'), 'display': T(32368, 'Unwatched')}
    },
    'artist': {
        'lastViewedAt': {'title': T(32369, 'By Date Played'), 'display': T(32370, 'Date Played')}
    },
    'photo': {
        'originallyAvailableAt': {'title': T(32373, 'By Date Taken'), 'display': T(32374, 'Date Taken')}
    },
    'photodirectory': {}
}


class ChunkRequestTask(backgroundthread.Task):
    def setup(self, section, start, size, callback, filter_=None, sort=None, unwatched=False):
        self.section = section
        self.start = start
        self.size = size
        self.callback = callback
        self.filter = filter_
        self.sort = sort
        self.unwatched = unwatched
        return self

    def contains(self, pos):
        return self.start <= pos <= (self.start + self.size)

    def run(self):
        if self.isCanceled():
            return

        try:
            items = self.section.all(self.start, self.size, self.filter, self.sort, self.unwatched)
            if self.isCanceled():
                return
            self.callback(items, self.start)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on section: {0}'.format(repr(self.section.title)))


class PhotoPropertiesTask(backgroundthread.Task):
    def setup(self, photo, callback):
        self.photo = photo
        self.callback = callback
        return self

    def run(self):
        if self.isCanceled():
            return

        try:
            self.photo.reload()
            self.callback(self.photo)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on photo reload: {0}'.format(self.photo))


class LibrarySettings(object):
    def __init__(self, section_or_server_id):
        if isinstance(section_or_server_id, basestring):
            self.serverID = section_or_server_id
            self.sectionID = None
        else:
            self.serverID = section_or_server_id.getServer().uuid
            self.sectionID = section_or_server_id.key

        self._loadSettings()

    def _loadSettings(self):
        jsonString = util.getSetting('library.settings.{0}'.format(self.serverID), '')
        self._settings = {}
        try:
            self._settings = json.loads(jsonString)
        except ValueError:
            pass
        except:
            util.ERROR()

    def _saveSettings(self):
        jsonString = json.dumps(self._settings)
        util.setSetting('library.settings.{0}'.format(self.serverID), jsonString)

    def setSection(self, section_id):
        self.sectionID = section_id

    def getSetting(self, setting, default=None):
        if not self._settings or self.sectionID not in self._settings:
            return default

        return self._settings[self.sectionID].get(setting, default)

    def setSetting(self, setting, value):
        if self.sectionID not in self._settings:
            self._settings[self.sectionID] = {}
        self._settings[self.sectionID][setting] = value

        self._saveSettings()


class LibraryWindow(kodigui.MultiWindow, windowutils.UtilMixin):
    bgXML = 'script-plex-blank.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'

    def __init__(self, *args, **kwargs):
        kodigui.MultiWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.section = kwargs.get('section')
        self.filter = kwargs.get('filter_')
        self.keyItems = {}
        self.firstOfKeyItems = {}
        self.tasks = []
        self.backgroundSet = False
        self.showPanelControl = None
        self.keyListControl = None
        self.lastItem = None
        self.librarySettings = LibrarySettings(self.section)
        self.filterUnwatched = self.librarySettings.getSetting('filter.unwatched', False)
        self.sort = self.librarySettings.getSetting('sort', 'titleSort')
        self.sortDesc = self.librarySettings.getSetting('sort.desc', False)
        self.lock = threading.Lock()

    def doClose(self):
        for task in self.tasks:
            task.cancel()
        kodigui.MultiWindow.doClose(self)

    def onFirstInit(self):
        if self.showPanelControl:
            self.showPanelControl.newControl(self)
            self.keyListControl.newControl(self)
            self.setFocusId(self.VIEWTYPE_BUTTON_ID)
        else:
            self.showPanelControl = kodigui.ManagedControlList(self, self.POSTERS_PANEL_ID, 5)
            self.keyListControl = kodigui.ManagedControlList(self, self.KEY_LIST_ID, 27)
            self.setProperty('no.options', self.section.TYPE != 'photodirectory' and '1' or '')
            self.setProperty('unwatched.hascount', self.section.TYPE == 'show' and '1' or '')
            self.setProperty('sort', self.sort)
            self.setProperty('filter1.display', self.filterUnwatched and T(32368, 'UNWATCHED') or T(32345, 'All'))
            self.setProperty('sort.display', SORT_KEYS[self.section.TYPE].get(self.sort, SORT_KEYS['movie'].get(self.sort))['title'])
            self.setProperty('media.type', TYPE_PLURAL.get(self.section.TYPE, self.section.TYPE))
            self.setProperty('media', self.section.TYPE)
            self.setProperty('hide.filteroptions', self.section.TYPE == 'photodirectory' and '1' or '')

            self.setTitle()
            self.fill()
            if self.getProperty('no.content') or self.getProperty('no.content.filtered'):
                self.setFocusId(self.HOME_BUTTON_ID)
            else:
                self.setFocusId(self.POSTERS_PANEL_ID)

    def onAction(self, action):
        try:
            if action.getId() in MOVE_SET:
                controlID = self.getFocusId()
                if controlID == self.POSTERS_PANEL_ID or controlID == self.SCROLLBAR_ID:
                    self.updateKey()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    if xbmc.getCondVisibility('IntegerGreaterThan(Container(101).ListItem.Property(index),5)'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            self.updateItem()

        except:
            util.ERROR()

        kodigui.MultiWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.POSTERS_PANEL_ID:
            self.showPanelClicked()
        elif controlID == self.KEY_LIST_ID:
            self.keyClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.VIEWTYPE_BUTTON_ID:
            self.viewTypeButtonClicked()
        elif controlID == self.SORT_BUTTON_ID:
            self.sortButtonClicked()
        elif controlID == self.FILTER1_BUTTON_ID:
            self.filter1ButtonClicked()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def onFocus(self, controlID):
        if controlID == self.KEY_LIST_ID:
            self.selectKey()

    def onItemChanged(self, mli):
        if not mli:
            return

        if not mli.dataSource or not mli.dataSource.TYPE == 'photo':
            return

        self.showPhotoItemProperties(mli.dataSource)

    def updateKey(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        if self.lastItem != mli:
            self.lastItem = mli
            self.onItemChanged(mli)

        self.setProperty('key', mli.getProperty('key'))

        self.selectKey(mli)

    def selectKey(self, mli=None):
        if not mli:
            mli = self.showPanelControl.getSelectedItem()
            if not mli:
                return

        li = self.keyItems.get(mli.getProperty('key'))
        if not li:
            return
        self.keyListControl.selectItem(li.pos())

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.section.key))

    def keyClicked(self):
        li = self.keyListControl.getSelectedItem()
        if not li:
            return

        mli = self.firstOfKeyItems.get(li.dataSource)
        if not mli:
            return

        self.showPanelControl.selectItem(mli.pos())
        self.setFocusId(self.POSTERS_PANEL_ID)
        self.setProperty('key', li.dataSource)

    def playButtonClicked(self, shuffle=False):
        filter_ = self.getFilterOpts()
        sort = self.getSortOpts()
        args = {}
        if filter_:
            args[filter_[0]] = filter_[1]

        if sort:
            args['sort'] = '{0}:{1}'.format(*sort)

        if self.section.TYPE == 'movie':
            args['sourceType'] = '1'
        elif self.section.TYPE == 'show':
            args['sourceType'] = '2'
        else:
            args['sourceType'] = '8'

        pq = playqueue.createPlayQueueForItem(self.section, options={'shuffle': shuffle}, args=args)
        opener.open(pq)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        # if self.section.TYPE not in ('artist', 'photo', 'photodirectory'):
        #     options.append({'key': 'mark_watched', 'display': 'Mark All Watched'})
        #     options.append({'key': 'mark_unwatched', 'display': 'Mark All Unwatched'})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})

        if self.section.TYPE == 'photodirectory':
            if options:
                options.append(dropdown.SEPARATOR)
            options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.section.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, (255, 205))
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'to_section':
            self.goHome(self.section.getLibrarySectionId())

    def sortButtonClicked(self):
        desc = 'script.plex/indicators/arrow-down.png'
        asc = 'script.plex/indicators/arrow-up.png'
        ind = self.sortDesc and desc or asc

        options = []

        if self.section.TYPE == 'movie':
            for stype in ('addedAt', 'originallyAvailableAt', 'lastViewedAt', 'titleSort', 'rating', 'resolution', 'duration'):
                option = SORT_KEYS['movie'].get(stype).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                options.append(option)
        elif self.section.TYPE == 'show':
            for stype in ('addedAt', 'lastViewedAt', 'originallyAvailableAt', 'titleSort', 'rating', 'unviewedLeafCount'):
                option = SORT_KEYS['show'].get(stype, SORT_KEYS['movie'].get(stype)).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                options.append(option)
        elif self.section.TYPE == 'artist':
            for stype in ('addedAt', 'lastViewedAt', 'viewCount', 'titleSort'):
                option = SORT_KEYS['artist'].get(stype, SORT_KEYS['movie'].get(stype)).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                options.append(option)
        elif self.section.TYPE == 'photo':
            for stype in ('addedAt', 'originallyAvailableAt', 'titleSort', 'rating'):
                option = SORT_KEYS['photo'].get(stype, SORT_KEYS['movie'].get(stype)).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                options.append(option)
        else:
            return

        result = dropdown.showDropdown(options, (1280, 106), with_indicator=True)
        if not result:
            return

        choice = result['type']

        if choice == self.sort:
            self.sortDesc = not self.sortDesc
        else:
            self.sortDesc = False

        self.sort = choice

        self.librarySettings.setSetting('sort', self.sort)
        self.librarySettings.setSetting('sort.desc', self.sortDesc)

        self.setProperty('sort', choice)
        self.setProperty('sort.display', result['title'])

        self.sortShowPanel(choice)

    def viewTypeButtonClicked(self):
        with self.lock:
            self.showPanelControl.invalidate()
            win = self.nextWindow()

        key = self.section.key
        if not key.isdigit():
            key = self.section.getLibrarySectionId()
        util.setSetting('viewtype.{0}.{1}'.format(self.section.server.uuid, key), win.VIEWTYPE)

    def sortShowPanel(self, choice):
        if choice == 'addedAt':
            self.showPanelControl.sort(lambda i: i.dataSource.addedAt, reverse=self.sortDesc)
        elif choice == 'originallyAvailableAt':
            self.showPanelControl.sort(lambda i: i.dataSource.get('originallyAvailableAt'), reverse=self.sortDesc)
        elif choice == 'lastViewedAt':
            self.showPanelControl.sort(lambda i: i.dataSource.get('lastViewedAt'), reverse=self.sortDesc)
        elif choice == 'viewCount':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('viewCount').asInt(), reverse=self.sortDesc)
        elif choice == 'titleSort':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title, reverse=self.sortDesc)
            self.keyListControl.sort(lambda i: i.getProperty('original'), reverse=self.sortDesc)
        elif choice == 'rating':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('rating').asFloat(), reverse=self.sortDesc)
        elif choice == 'resolution':
            self.showPanelControl.sort(lambda i: i.dataSource.maxHeight, reverse=self.sortDesc)
        elif choice == 'duration':
            self.showPanelControl.sort(lambda i: i.dataSource.duration.asInt(), reverse=self.sortDesc)
        elif choice == 'unviewedLeafCount':
            self.showPanelControl.sort(lambda i: i.dataSource.unViewedLeafCount, reverse=self.sortDesc)

        for i, mli in enumerate(self.showPanelControl):
            mli.setProperty('index', str(i))

    def subOptionCallback(self, option):
        check = 'script.plex/home/device/check.png'
        options = None
        subKey = None
        if self.filter:
            if self.filter.get('sub'):
                subKey = self.filter['sub']['val']

        if option['type'] in (
            'year', 'decade', 'genre', 'contentRating', 'collection', 'director', 'actor', 'country', 'studio', 'resolution', 'labels',
            'make', 'model', 'aperture', 'exposure', 'iso', 'lens'
        ):
            options = [{'val': o.key, 'display': o.title, 'indicator': o.key == subKey and check or ''} for o in self.section.listChoices(option['type'])]
            if not options:
                options = [{'val': None, 'display': T(32375, 'No filters available'), 'ignore': True}]

        return options

    def hasFilter(self, ftype):
        if not self.filter:
            return False

        return self.filter['type'] == ftype

    def filter1ButtonClicked(self):
        check = 'script.plex/home/device/check.png'

        options = []

        if self.section.TYPE in ('movie', 'show'):
            options.append({'type': 'unwatched', 'display': T(32368, 'UNWATCHED').upper(), 'indicator': self.filterUnwatched and check or ''})

        if self.filter:
            options.append({'type': 'clear_filter', 'display': T(32376, 'CLEAR FILTER').upper(), 'indicator': 'script.plex/indicators/remove.png'})

        if options:
            options.append(None)  # Separator

        optionsMap = {
            'year': {'type': 'year', 'display': T(32377, 'Year'), 'indicator': self.hasFilter('year') and check or ''},
            'decade': {'type': 'decade', 'display': T(32378, 'Decade'), 'indicator': self.hasFilter('decade') and check or ''},
            'genre': {'type': 'genre', 'display': T(32379, 'Genre'), 'indicator': self.hasFilter('genre') and check or ''},
            'contentRating': {'type': 'contentRating', 'display': T(32380, 'Content Rating'), 'indicator': self.hasFilter('contentRating') and check or ''},
            'network': {'type': 'studio', 'display': T(32381, 'Network'), 'indicator': self.hasFilter('studio') and check or ''},
            'collection': {'type': 'collection', 'display': T(32382, 'Collection'), 'indicator': self.hasFilter('collection') and check or ''},
            'director': {'type': 'director', 'display': T(32383, 'Director'), 'indicator': self.hasFilter('director') and check or ''},
            'actor': {'type': 'actor', 'display': T(32384, 'Actor'), 'indicator': self.hasFilter('actor') and check or ''},
            'country': {'type': 'country', 'display': T(32385, 'Country'), 'indicator': self.hasFilter('country') and check or ''},
            'studio': {'type': 'studio', 'display': T(32386, 'Studio'), 'indicator': self.hasFilter('studio') and check or ''},
            'resolution': {'type': 'resolution', 'display': T(32362, 'Resolution'), 'indicator': self.hasFilter('resolution') and check or ''},
            'labels': {'type': 'labels', 'display': T(32387, 'Labels'), 'indicator': self.hasFilter('labels') and check or ''},

            'make': {'type': 'make', 'display': T(32388, 'Camera Make'), 'indicator': self.hasFilter('make') and check or ''},
            'model': {'type': 'model', 'display': T(32389, 'Camera Model'), 'indicator': self.hasFilter('model') and check or ''},
            'aperture': {'type': 'aperture', 'display': T(32390, 'Aperture'), 'indicator': self.hasFilter('aperture') and check or ''},
            'exposure': {'type': 'exposure', 'display': T(32391, 'Shutter Speed'), 'indicator': self.hasFilter('exposure') and check or ''},
            'iso': {'type': 'iso', 'display': 'ISO', 'indicator': self.hasFilter('iso') and check or ''},
            'lens': {'type': 'lens', 'display': T(32392, 'Lens'), 'indicator': self.hasFilter('lens') and check or ''}
        }

        if self.section.TYPE == 'movie':
            for k in ('year', 'decade', 'genre', 'contentRating', 'collection', 'director', 'actor', 'country', 'studio', 'resolution', 'labels'):
                options.append(optionsMap[k])
        elif self.section.TYPE == 'show':
            for k in ('year', 'genre', 'contentRating', 'network', 'collection', 'actor', 'labels'):
                options.append(optionsMap[k])
        elif self.section.TYPE == 'artist':
            for k in ('genre', 'country', 'collection'):
                options.append(optionsMap[k])
        elif self.section.TYPE == 'photo':
            for k in ('year', 'make', 'model', 'aperture', 'exposure', 'iso', 'lens', 'labels'):
                options.append(optionsMap[k])

        result = dropdown.showDropdown(options, (980, 106), with_indicator=True, suboption_callback=self.subOptionCallback)
        if not result:
            return

        choice = result['type']

        if choice == 'clear_filter':
            self.filter = None
        elif choice == 'unwatched':
            self.filterUnwatched = not self.filterUnwatched
            self.librarySettings.setSetting('filter.unwatched', self.filterUnwatched)
        else:
            self.filter = result

        self.updateFilterDisplay()

        if self.filter or choice in ('clear_filter', 'unwatched'):
            self.fill()

    def updateFilterDisplay(self):
        if self.filter:
            disp = self.filter['display']
            if self.filter.get('sub'):
                disp = u'{0}: {1}'.format(disp, self.filter['sub']['display'])
            self.setProperty('filter1.display', disp)
            self.setProperty('filter2.display', self.filterUnwatched and 'unwatched' or '')
        else:
            self.setProperty('filter2.display', '')
            self.setProperty('filter1.display', self.filterUnwatched and 'unwatched' or 'all')

    def showPanelClicked(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli or not mli.dataSource:
            return

        updateWatched = False
        if self.section.TYPE == 'show':
            self.processCommand(opener.handleOpen(subitems.ShowWindow, media_item=mli.dataSource, parent_list=self.showPanelControl))
            updateWatched = True
        elif self.section.TYPE == 'movie':
            self.processCommand(opener.handleOpen(preplay.PrePlayWindow, video=mli.dataSource, parent_list=self.showPanelControl))
            updateWatched = True
        elif self.section.TYPE == 'artist':
            self.processCommand(opener.handleOpen(subitems.ArtistWindow, media_item=mli.dataSource, parent_list=self.showPanelControl))
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.showPhoto(mli.dataSource)

        if not mli.dataSource.exists():
            self.showPanelControl.removeItem(mli.pos())
            return

        if updateWatched:
            self.updateUnwatched(mli)

    def showPhoto(self, photo):
        if isinstance(photo, plexnet.photo.Photo) or photo.TYPE == 'clip':
            self.processCommand(opener.open(photo))
        else:
            self.processCommand(opener.sectionClicked(photo))

    def updateUnwatched(self, mli):
        mli.dataSource.reload()
        if mli.dataSource.isWatched:
            mli.setProperty('unwatched', '')
            mli.setProperty('unwatched.count', '')
        else:
            if self.section.TYPE == 'show':
                mli.setProperty('unwatched.count', str(mli.dataSource.unViewedLeafCount))
            else:
                mli.setProperty('unwatched', '1')

    def setTitle(self):
        if self.section.TYPE == 'artist':
            self.setProperty('screen.title', T(32394, 'MUSIC').upper())
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.setProperty('screen.title', T(32349, 'photos').upper())
        else:
            self.setProperty('screen.title', self.section.TYPE == 'show' and T(32393, 'TV SHOWS').upper() or T(32348, 'movies').upper())

        self.updateFilterDisplay()

    def updateItem(self, mli=None):
        mli = mli or self.showPanelControl.getSelectedItem()
        if not mli or mli.dataSource:
            return

        for task in self.tasks:
            if task.contains(mli.pos()):
                util.DEBUG_LOG('Moving task to front: {0}'.format(task))
                backgroundthread.BGThreader.moveToFront(task)
                break

    def setBackground(self, items):
        if self.backgroundSet:
            return
        self.backgroundSet = True

        item = random.choice(items)
        self.setProperty('background', item.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))

    def fill(self):
        if self.section.TYPE in ('photo', 'photodirectory'):
            self.fillPhotos()
        else:
            self.fillShows()

    def getFilterOpts(self):
        if not self.filter:
            return None

        if not self.filter.get('sub'):
            util.DEBUG_LOG('Filter missing sub-filter data')
            return None

        return (self.filter['type'], urllib.unquote_plus(self.filter['sub']['val']))

    def getSortOpts(self):
        if not self.sort:
            return None

        return (self.sort, self.sortDesc and 'desc' or 'asc')

    @busy.dialog()
    def fillShows(self):
        self.setBoolProperty('no.content', False)
        self.setBoolProperty('no.content.filtered', False)
        items = []
        jitems = []
        self.keyItems = {}
        self.firstOfKeyItems = {}
        totalSize = 0

        jumpList = self.section.jumpList(filter_=self.getFilterOpts(), sort=self.getSortOpts(), unwatched=self.filterUnwatched)
        idx = 0
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

        if not jumpList:
            if self.filter or self.filterUnwatched:
                self.setBoolProperty('no.content.filtered', True)
            else:
                self.setBoolProperty('no.content', True)
            return

        for kidx, ji in enumerate(jumpList):
            mli = kodigui.ManagedListItem(ji.title, data_source=ji.key)
            mli.setProperty('key', ji.key)
            mli.setProperty('original', '{0:02d}'.format(kidx))
            self.keyItems[ji.key] = mli
            jitems.append(mli)
            totalSize += ji.size.asInt()

            for x in range(ji.size.asInt()):
                mli = kodigui.ManagedListItem('')
                mli.setProperty('key', ji.key)
                mli.setProperty('thumb.fallback', fallback)
                mli.setProperty('index', str(idx))
                items.append(mli)
                if not x:  # i.e. first item
                    self.firstOfKeyItems[ji.key] = mli
                idx += 1

        self.showPanelControl.reset()
        self.keyListControl.reset()

        self.showPanelControl.addItems(items)
        self.keyListControl.addItems(jitems)

        if jumpList:
            self.setProperty('key', jumpList[0].key)

        tasks = []
        for start in range(0, totalSize, 500):
            tasks.append(
                ChunkRequestTask().setup(
                    self.section, start, 500, self.chunkCallback, filter_=self.getFilterOpts(), sort=self.getSortOpts(), unwatched=self.filterUnwatched
                )
            )

        self.tasks = tasks
        backgroundthread.BGThreader.addTasksToFront(tasks)

    def showPhotoItemProperties(self, photo):
        if photo.isFullObject():
            return

        task = PhotoPropertiesTask().setup(photo, self._showPhotoItemProperties)
        backgroundthread.BGThreader.addTasksToFront([task])

    def _showPhotoItemProperties(self, photo):
        mli = self.showPanelControl.getSelectedItem()
        if not mli or not mli.dataSource.TYPE == 'photo':
            for mli in self.showPanelControl:
                if mli.dataSource == photo:
                    break
            else:
                return

        mli.setProperty('camera.model', photo.media[0].model)
        mli.setProperty('camera.lens', photo.media[0].lens)

        attrib = []
        if photo.media[0].height:
            attrib.append(u'{0} x {1}'.format(photo.media[0].width, photo.media[0].height))

        orientation = photo.media[0].parts[0].orientation
        if orientation:
            attrib.append(u'{0} Mo'.format(orientation))

        container = photo.media[0].container_ or os.path.splitext(photo.media[0].parts[0].file)[-1][1:].lower()
        if container == 'jpg':
            container = 'jpeg'
        attrib.append(container.upper())
        if attrib:
            mli.setProperty('photo.dims', u' \u2022 '.join(attrib))

        settings = []
        if photo.media[0].iso:
            settings.append('ISO {0}'.format(photo.media[0].iso))
        if photo.media[0].aperture:
            settings.append('{0}'.format(photo.media[0].aperture))
        if photo.media[0].exposure:
            settings.append('{0}'.format(photo.media[0].exposure))
        mli.setProperty('camera.settings', u' \u2022 '.join(settings))
        mli.setProperty('photo.summary', photo.get('summary'))

    @busy.dialog()
    def fillPhotos(self):
        self.setBoolProperty('no.content', False)
        self.setBoolProperty('no.content.filtered', False)
        items = []
        keys = []
        self.firstOfKeyItems = {}
        idx = 0

        if self.section.TYPE == 'photodirectory':
            photos = self.section.all()
        else:
            photos = self.section.all(filter_=self.getFilterOpts(), sort=self.getSortOpts(), unwatched=self.filterUnwatched)

        if not photos:
            return

        photo = random.choice(photos)
        self.setProperty('background', photo.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))
        thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

        if not photos:
            if self.filter or self.filterUnwatched:
                self.setBoolProperty('no.content.filtered', True)
            else:
                self.setBoolProperty('no.content', True)
            return

        for photo in photos:
            title = photo.title
            if photo.TYPE == 'photodirectory':
                thumb = photo.composite.asTranscodedImageURL(*thumbDim)
                mli = kodigui.ManagedListItem(title, thumbnailImage=thumb, data_source=photo)
                mli.setProperty('is.folder', '1')
            else:
                thumb = photo.defaultThumb.asTranscodedImageURL(*thumbDim)
                label2 = util.cleanLeadingZeros(photo.originallyAvailableAt.asDatetime('%d %B %Y'))
                mli = kodigui.ManagedListItem(title, label2, thumbnailImage=thumb, data_source=photo)

            mli.setProperty('thumb.fallback', fallback)
            mli.setProperty('index', str(idx))

            key = title[0].upper()
            if key not in KEYS:
                key = '#'
            if key not in keys:
                self.firstOfKeyItems[key] = mli
                keys.append(key)
            mli.setProperty('key', str(key))
            items.append(mli)
            idx += 1

        litems = []
        self.keyItems = {}
        for i, key in enumerate(keys):
            mli = kodigui.ManagedListItem(key, data_source=key)
            mli.setProperty('key', key)
            mli.setProperty('original', '{0:02d}'.format(i))
            self.keyItems[key] = mli
            litems.append(mli)

        self.showPanelControl.reset()
        self.keyListControl.reset()

        self.showPanelControl.addItems(items)
        self.keyListControl.addItems(litems)

        if keys:
            self.setProperty('key', keys[0])

    def chunkCallback(self, items, start):
        with self.lock:
            pos = start
            self.setBackground(items)
            thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
            artDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie']).get('art_dim', (256, 256))

            showUnwatched = self.section.TYPE in ('movie', 'show') and True or False

            for obj in items:
                mli = self.showPanelControl[pos]
                mli.setLabel(obj.defaultTitle or '')
                mli.setThumbnailImage(obj.defaultThumb.asTranscodedImageURL(*thumbDim))
                mli.dataSource = obj
                mli.setProperty('summary', obj.get('summary'))

                if showUnwatched:
                    mli.setLabel2(util.durationToText(obj.fixedDuration()))
                    mli.setProperty('art', obj.defaultArt.asTranscodedImageURL(*artDim))
                    if not obj.isWatched:
                        if self.section.TYPE == 'show':
                            mli.setProperty('unwatched.count', str(obj.unViewedLeafCount))
                        else:
                            mli.setProperty('unwatched', '1')

                pos += 1


class PostersWindow(kodigui.ControlledWindow):
    xmlFile = 'script-plex-posters.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    POSTERS_PANEL_ID = 101
    KEY_LIST_ID = 151
    SCROLLBAR_ID = 152

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    SORT_BUTTON_ID = 210
    FILTER1_BUTTON_ID = 211
    FILTER2_BUTTON_ID = 212

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    VIEWTYPE_BUTTON_ID = 304

    VIEWTYPE = 'panel'


class ListView16x9Window(PostersWindow):
    xmlFile = 'script-plex-listview-16x9.xml'
    VIEWTYPE = 'list'


class SquaresWindow(PostersWindow):
    xmlFile = 'script-plex-squares.xml'
    VIEWTYPE = 'panel'


class ListViewSquareWindow(PostersWindow):
    xmlFile = 'script-plex-listview-square.xml'
    VIEWTYPE = 'list'


VIEWS_POSTER = {
    'panel': PostersWindow,
    'list': ListView16x9Window
}

VIEWS_SQUARE = {
    'panel': SquaresWindow,
    'list': ListViewSquareWindow
}
