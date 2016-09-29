import random
import urllib

import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util
from lib import backgroundthread

import busy
import subitems
import preplay
import plexnet
import dropdown
import opener
import windowutils

from plexnet import playqueue

KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

MOVE_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_MOVE_UP,
        xbmcgui.ACTION_MOVE_DOWN,
        xbmcgui.ACTION_MOUSE_MOVE,
        xbmcgui.ACTION_PAGE_UP,
        xbmcgui.ACTION_PAGE_DOWN
    )
)

THUMB_POSTER_DIM = (287, 425)
THUMB_AR16X9_DIM = (619, 348)
THUMB_SQUARE_DIM = (425, 425)

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
        'thumb_dim': THUMB_POSTER_DIM
    },
    'show': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM
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
        'thumb_dim': THUMB_AR16X9_DIM
    },
}

TYPE_PLURAL = {
    'artist': 'artists',
    'movie': 'movies',
    'photo': 'photos',
    'show': 'shows'
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


class PostersWindow(kodigui.BaseWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-posters.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    POSTERS_PANEL_ID = 101
    KEY_LIST_ID = 151

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    PLAYER_STATUS_BUTTON_ID = 204

    SORT_BUTTON_ID = 210
    FILTER1_BUTTON_ID = 211
    FILTER2_BUTTON_ID = 212

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    VIEWTYPE_BUTTON_ID = 304

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.section = kwargs.get('section')
        self.keyItems = {}
        self.firstOfKeyItems = {}
        self.tasks = []
        self.backgroundSet = False
        self.exitCommand = None
        self.sort = 'titleSort'
        self.sortDesc = False
        self.filter = None
        self.filterUnwatched = False

    def doClose(self):
        for task in self.tasks:
            task.cancel()
        kodigui.BaseWindow.doClose(self)

    def onFirstInit(self):
        self.showPanelControl = kodigui.ManagedControlList(self, self.POSTERS_PANEL_ID, 5)
        self.keyListControl = kodigui.ManagedControlList(self, self.KEY_LIST_ID, 27)
        self.setProperty('no.options', self.section.TYPE != 'photodirectory' and '1' or '')
        self.setProperty('unwatched.hascount', self.section.TYPE == 'show' and '1' or '')
        self.setProperty('sort', self.sort)
        self.setProperty('filter1.display', 'All')
        self.setProperty('sort.display', 'By Name')
        self.setProperty('media.type', TYPE_PLURAL.get(self.section.TYPE, self.section.TYPE))
        self.setProperty('hide.filteroptions', self.section.TYPE == 'photodirectory' and '1' or '')

        self.setTitle()
        self.fill()
        self.setFocusId(self.POSTERS_PANEL_ID)

    def onAction(self, action):
        try:
            if action.getId() in MOVE_SET:
                controlID = self.getFocusId()
                if controlID == self.POSTERS_PANEL_ID:
                    self.updateKey()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return

            self.updateItem()

        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.closeWithCommand('HOME')
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
        elif controlID == self.SORT_BUTTON_ID:
            self.sortButtonClicked()
        elif controlID == self.FILTER1_BUTTON_ID:
            self.filter1ButtonClicked()

    def onFocus(self, controlID):
        if controlID == self.KEY_LIST_ID:
            self.selectKey()

    def updateKey(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        self.setProperty('key', mli.getProperty('key'))

    def selectKey(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        li = self.keyItems.get(mli.getProperty('key'))
        if not li:
            return
        self.keyListControl.selectItem(li.pos())

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
        pq = playqueue.createPlayQueueForItem(self.section, options={'shuffle': shuffle})
        opener.open(pq)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': 'Play Next'})

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
            options.append({'key': 'to_section', 'display': u'Go to {0}'.format(self.section.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, (255, 260))
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'to_section':
            self.closeWithCommand('HOME:{0}'.format(self.section.getLibrarySectionId()))

    def sortButtonClicked(self):
        desc = 'script.plex/indicators/arrow-down.png'
        asc = 'script.plex/indicators/arrow-up.png'
        ind = self.sortDesc and desc or asc

        if self.section.TYPE == 'movie':
            options = [
                {'type': 'addedAt', 'title': 'By Date Added', 'display': 'Date Added', 'indicator': self.sort == 'addedAt' and ind or ''},
                {
                    'type': 'originallyAvailableAt', 'title': 'By Release Date',
                    'display': 'Release Date', 'indicator': self.sort == 'originallyAvailableAt' and ind or ''
                },
                {'type': 'lastViewedAt', 'title': 'By Date Viewed', 'display': 'Date Viewed', 'indicator': self.sort == 'lastViewedAt' and ind or ''},
                {'type': 'titleSort', 'title': 'By Name', 'display': 'Name', 'indicator': self.sort == 'titleSort' and ind or ''},
                {'type': 'rating', 'title': 'By Rating', 'display': 'Rating', 'indicator': self.sort == 'rating' and ind or ''},
                {'type': 'resolution', 'title': 'By Resolution', 'display': 'Resolution', 'indicator': self.sort == 'resolution' and ind or ''},
                {'type': 'duration', 'title': 'By Duration', 'display': 'Duration', 'indicator': self.sort == 'duration' and ind or ''}
            ]
        elif self.section.TYPE == 'show':
            options = [
                {'type': 'addedAt', 'title': 'By Date Added', 'display': 'Date Added', 'indicator': self.sort == 'addedAt' and ind or ''},
                {'type': 'lastViewedAt', 'title': 'By Date Viewed', 'display': 'Date Viewed', 'indicator': self.sort == 'lastViewedAt' and ind or ''},
                {
                    'type': 'originallyAvailableAt', 'title': 'By First Aired',
                    'display': 'First Aired', 'indicator': self.sort == 'originallyAvailableAt' and ind or ''
                },
                {'type': 'titleSort', 'title': 'By Name', 'display': 'Name', 'indicator': self.sort == 'titleSort' and ind or ''},
                {'type': 'rating', 'title': 'By Rating', 'display': 'Rating', 'indicator': self.sort == 'rating' and ind or ''},
                {'type': 'unwatched', 'title': 'By Unwatched', 'display': 'Unwatched', 'indicator': self.sort == 'unwatched' and ind or ''}
            ]
        elif self.section.TYPE == 'artist':
            options = [
                {'type': 'addedAt', 'title': 'By Date Added', 'display': 'Date Added', 'indicator': self.sort == 'addedAt' and ind or ''},
                {'type': 'lastViewedAt', 'title': 'By Date Played', 'display': 'Date Played', 'indicator': self.sort == 'lastViewedAt' and ind or ''},
                {'type': 'viewCount', 'title': 'By Play Count', 'display': 'Play Count', 'indicator': self.sort == 'viewCount' and ind or ''},
                {'type': 'titleSort', 'title': 'By Name', 'display': 'Name', 'indicator': self.sort == 'titleSort' and ind or ''}
            ]
        elif self.section.TYPE == 'photo':
            options = [
                {'type': 'addedAt', 'title': 'By Date Added', 'display': 'Date Added', 'indicator': self.sort == 'addedAt' and ind or ''},
                {
                    'type': 'originallyAvailableAt', 'title': 'By Date Taken',
                    'display': 'Date Taken', 'indicator': self.sort == 'originallyAvailableAt' and ind or ''
                },
                {'type': 'titleSort', 'title': 'By Name', 'display': 'Name', 'indicator': self.sort == 'titleSort' and ind or ''},
                {'type': 'rating', 'title': 'By Rating', 'display': 'Rating', 'indicator': self.sort == 'rating' and ind or ''}
            ]
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
        self.setProperty('sort', choice)
        self.setProperty('sort.display', result['display'])

        self.sortShowPanel(choice)

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
        elif choice == 'unwatched':
            self.showPanelControl.sort(lambda i: i.dataSource.unViewedLeafCount, reverse=self.sortDesc)

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
                options = [{'val': None, 'display': 'No filters available', 'ignore': True}]

        return options

    def hasFilter(self, ftype):
        if not self.filter:
            return False

        return self.filter['type'] == ftype

    def filter1ButtonClicked(self):
        check = 'script.plex/home/device/check.png'

        options = []

        if self.section.TYPE in ('movie', 'show'):
            options.append({'type': 'unwatched', 'display': 'UNWATCHED', 'indicator': self.filterUnwatched and check or ''})

        if self.filter:
            options.append({'type': 'clear_filter', 'display': 'CLEAR FILTER', 'indicator': 'script.plex/indicators/remove.png'})

        if options:
            options.append(None)  # Separator

        optionsMap = {
            'year': {'type': 'year', 'display': 'Year', 'indicator': self.hasFilter('year') and check or ''},
            'decade': {'type': 'decade', 'display': 'Decade', 'indicator': self.hasFilter('decade') and check or ''},
            'genre': {'type': 'genre', 'display': 'Genre', 'indicator': self.hasFilter('genre') and check or ''},
            'contentRating': {'type': 'contentRating', 'display': 'Content Rating', 'indicator': self.hasFilter('contentRating') and check or ''},
            'network': {'type': 'studio', 'display': 'Network', 'indicator': self.hasFilter('studio') and check or ''},
            'collection': {'type': 'collection', 'display': 'Collection', 'indicator': self.hasFilter('collection') and check or ''},
            'director': {'type': 'director', 'display': 'Director', 'indicator': self.hasFilter('director') and check or ''},
            'actor': {'type': 'actor', 'display': 'Actor', 'indicator': self.hasFilter('actor') and check or ''},
            'country': {'type': 'country', 'display': 'Country', 'indicator': self.hasFilter('country') and check or ''},
            'studio': {'type': 'studio', 'display': 'Studio', 'indicator': self.hasFilter('studio') and check or ''},
            'resolution': {'type': 'resolution', 'display': 'Resolution', 'indicator': self.hasFilter('resolution') and check or ''},
            'labels': {'type': 'labels', 'display': 'Labels', 'indicator': self.hasFilter('labels') and check or ''},

            'make': {'type': 'make', 'display': 'Camera Make', 'indicator': self.hasFilter('make') and check or ''},
            'model': {'type': 'model', 'display': 'Camera Model', 'indicator': self.hasFilter('model') and check or ''},
            'aperture': {'type': 'aperture', 'display': 'Aperture', 'indicator': self.hasFilter('aperture') and check or ''},
            'exposure': {'type': 'exposure', 'display': 'Shutter Speed', 'indicator': self.hasFilter('exposure') and check or ''},
            'iso': {'type': 'iso', 'display': 'ISO', 'indicator': self.hasFilter('iso') and check or ''},
            'lens': {'type': 'lens', 'display': 'Lens', 'indicator': self.hasFilter('lens') and check or ''}
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
        else:
            self.filter = result

        if self.filter:
            disp = self.filter['display']
            if self.filter.get('sub'):
                disp = self.filter['sub']['display']
            self.setProperty('filter1.display', disp)
            self.setProperty('filter2.display', self.filterUnwatched and 'unwatched' or '')
        else:
            self.setProperty('filter2.display', '')
            self.setProperty('filter1.display', self.filterUnwatched and 'unwatched' or 'all')

        if self.filter or choice in ('clear_filter', 'unwatched'):
            self.fill()

    def showPanelClicked(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli or not mli.dataSource:
            return

        if self.section.TYPE == 'show':
            self.showSeasons(mli.dataSource)
            self.updateUnwatched(mli)
        elif self.section.TYPE == 'movie':
            self.showPreplay(mli.dataSource)
            self.updateUnwatched(mli)
        elif self.section.TYPE == 'artist':
            self.showArtist(mli.dataSource)
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.showPhoto(mli.dataSource)

    def showSeasons(self, show):
        w = subitems.ShowWindow.open(media_item=show)
        self.onChildWindowClosed(w)

    def showPreplay(self, movie):
        w = preplay.PrePlayWindow.open(video=movie)
        self.onChildWindowClosed(w)

    def showArtist(self, artist):
        w = subitems.ArtistWindow.open(media_item=artist)
        self.onChildWindowClosed(w)

    def showPhoto(self, photo):
        if isinstance(photo, plexnet.photo.Photo) or photo.TYPE == 'clip':
            self.processCommand(opener.open(photo))
        else:
            w = SquaresWindow.open(section=photo)
            self.onChildWindowClosed(w)

    def updateUnwatched(self, mli):
        mli.dataSource.reload()
        mli.setProperty('unwatched', not mli.dataSource.isWatched and '1' or '')
        if not mli.dataSource.isWatched and self.section.TYPE == 'show':
            mli.setProperty('unwatched.count', str(mli.dataSource.unViewedLeafCount))

    def onChildWindowClosed(self, w):
        try:
            self.processCommand(w.exitCommand)
        finally:
            del w

    def setTitle(self):
        if self.section.TYPE == 'artist':
            self.setProperty('screen.title', 'MUSIC')
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.setProperty('screen.title', 'PHOTOS')
        else:
            self.setProperty('screen.title', self.section.TYPE == 'show' and 'TV SHOWS' or 'MOVIES')

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
        items = []
        jitems = []
        self.keyItems = {}
        self.firstOfKeyItems = {}
        totalSize = 0

        jumpList = self.section.jumpList(filter_=self.getFilterOpts(), sort=self.getSortOpts(), unwatched=self.filterUnwatched)
        idx = 0
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

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

    @busy.dialog()
    def fillPhotos(self):
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

        for photo in photos:
            title = photo.title
            if photo.TYPE == 'photodirectory':
                thumb = photo.composite.asTranscodedImageURL(*thumbDim)
            else:
                thumb = photo.defaultThumb.asTranscodedImageURL(*thumbDim)
            mli = kodigui.ManagedListItem(title, thumbnailImage=thumb, data_source=photo)
            if photo.TYPE == 'photodirectory':
                mli.setProperty('is.folder', '1')
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
        pos = start
        self.setBackground(items)
        thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
        showUnwatched = self.section.TYPE in ('movie', 'show') and True or False

        for obj in items:
            mli = self.showPanelControl[pos]
            mli.setLabel(obj.defaultTitle or '')
            mli.setThumbnailImage(obj.defaultThumb.asTranscodedImageURL(*thumbDim))
            mli.dataSource = obj
            if showUnwatched:
                if not mli.dataSource.isWatched:
                    mli.setProperty('unwatched', '1')
                    if self.section.TYPE == 'show':
                        mli.setProperty('unwatched.count', str(obj.unViewedLeafCount))
            pos += 1


class SquaresWindow(PostersWindow):
    xmlFile = 'script-plex-squares.xml'
