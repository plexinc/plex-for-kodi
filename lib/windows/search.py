import time
import threading

import kodigui

from lib import util

from plexnet import plexapp


class SearchDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-search.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
    SECTION_BUTTONS = {
        901: 'all',
        902: 'movie',
        903: 'show',
        904: 'artist',
        905: 'photo'
    }

    HUB_POSTER_00 = 2100
    HUB_SQUARE_01 = 2101
    HUB_AR16X9_02 = 2102
    HUB_CIRCLE_03 = 2103
    HUB_POSTER_04 = 2104
    HUB_SQUARE_05 = 2105
    HUB_AR16X9_06 = 2106
    HUB_CIRCLE_07 = 2107
    HUB_POSTER_08 = 2108
    HUB_SQUARE_09 = 2109
    HUB_AR16X9_10 = 2110
    HUB_CIRCLE_11 = 2111
    HUB_POSTER_12 = 2112
    HUB_SQUARE_13 = 2113
    HUB_AR16X9_14 = 2114
    HUB_CIRCLE_15 = 2115

    HUBMAP = {
        'track': {'type': 'square'},
        'episode': {'type': 'ar16x9'},
        'movie': {'type': 'poster'},
        'show': {'type': 'poster'},
        'artist': {'type': 'square'},
        'album': {'type': 'square'},
        'photoalbum': {'type': 'square'},
        'photo': {'type': 'square'},
        'actor': {'type': 'circle'},
        'director': {'type': 'circle'},
        'genre': {'type': 'square'},
        'playlist': {'type': 'square'},
    }

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        # self.query = 'Not Implemented'
        self.query = ''
        self.resultsThread = None
        self.updateResultsTimeout = 0

    def onFirstInit(self):
        self.hubControls = (
            {
                'poster': kodigui.ManagedControlList(self, self.HUB_POSTER_00, 5),
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
            {
                'poster': None,
                'square': None,
                'ar16x9': None,
                'circle': None
            },
        )

        self.setProperty('search.section', 'all')
        self.updateQuery()

    def onAction(self, action):
        try:
            pass
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if 1000 < controlID < 1037:
            self.letterClicked(controlID)
        elif controlID in self.SECTION_BUTTONS:
            self.sectionClicked(controlID)
        elif controlID == 951:
            self.deleteClicked()
        elif controlID == 952:
            self.letterClicked(1037)
        elif controlID == 953:
            self.clearClicked()

    def updateQuery(self):
        self.setProperty('search.query', self.query)
        self.updateResults()

    def updateResults(self):
        self.updateResultsTimeout = time.time() + 1
        if not self.resultsThread or not self.resultsThread.isAlive():
            self.resultsThread = threading.Thread(target=self._updateResults, name='search.update')
            self.resultsThread.start()

    def _updateResults(self):
        while time.time() < self.updateResultsTimeout and not util.MONITOR.waitForAbort(0.1):
            pass

        self._reallyUpdateResults()

    def _reallyUpdateResults(self):
        if self.query:
            hubs = plexapp.SERVERMANAGER.selectedServer.hubs(search_query=self.query)
            self.showHubs(hubs)
        else:
            self.clearHubs()

    def sectionClicked(self, controlID):
        section = self.SECTION_BUTTONS[controlID]
        self.setProperty('search.section', section)

    def letterClicked(self, controlID):
        letter = self.LETTERS[controlID - 1001]
        self.query += letter
        self.updateQuery()

    def deleteClicked(self):
        self.query = self.query[:-1]
        self.updateQuery()

    def clearClicked(self):
        self.query = ''
        self.updateQuery()

    def showHubs(self, hubs):
        i = 0
        for h in hubs:
            if h.size.asInt() > 0:
                self.showHub(h, i)
                i += 1

    def showHub(self, hub, idx):
        util.DEBUG_LOG('Showing search hub: {0} at {1}'.format(hub.type, idx))
        info = self.HUBMAP.get(hub.type)
        if not info:
            util.DEBUG_LOG('Unhandled hub type: {0}'.format(hub.type))
            return

        itemListControl = self.hubControls[idx][info['type']]
        if itemListControl is None:
            util.DEBUG_LOG('No control defined')
            return

        self.setProperty('hub.{0}'.format(itemListControl.controlID), hub.title)

        items = []
        for hubItem in hub.items:
            mli = kodigui.ManagedListItem(hubItem.title, thumbnailImage=hubItem.defaultThumb.asTranscodedImageURL(256, 256), data_source=hubItem)
            items.append(mli)

        itemListControl.reset()
        itemListControl.addItems(items)

    def clearHubs(self):
        for controls in self.hubControls:
            for control in controls.values():
                if control:
                    control.reset()


def dialog():
    w = SearchDialog.open()
    del w
