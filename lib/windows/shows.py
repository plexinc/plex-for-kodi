import xbmc
import xbmcgui
import kodigui

from lib import util

import seasons

KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

MOVE_SET = ((xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOUSE_MOVE))


class ShowsWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-shows.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_POSTER_DIM = (287, 425)
    THUMB_AR16X9_DIM = (619, 348)
    THUMB_SQUARE_DIM = (425, 425)

    SHOW_PANEL_ID = 101
    KEY_LIST_ID = 151

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.section = kwargs.get('section')
        self.keyItems = {}
        self.firstOfKeyItems = {}
        self.exitCommand = None

    def onFirstInit(self):
        self.showPanelControl = kodigui.ManagedControlList(self, self.SHOW_PANEL_ID, 5)
        self.keyListControl = kodigui.ManagedControlList(self, self.KEY_LIST_ID, 27)

        self.fillShows()
        self.setFocusId(self.SHOW_PANEL_ID)

    def onAction(self, action):
        try:
            if action in MOVE_SET:
                controlID = self.getFocusId()
                if controlID == self.SHOW_PANEL_ID:
                    self.updateKey()
            # elif action == xbmcgui.ACTION_NAV_BACK:
            #     if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
            #         self.setFocusId(self.OPTIONS_GROUP_ID)
            #         return

        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.doClose()
        elif controlID == self.SHOW_PANEL_ID:
            self.showPanelClicked()
        elif controlID == self.KEY_LIST_ID:
            self.keyClicked()

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
        self.setFocusId(self.SHOW_PANEL_ID)
        self.setProperty('key', li.dataSource)

    def showPanelClicked(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        w = seasons.SeasonsWindow.open(show=mli.dataSource)
        try:
            if w.exitCommand == 'HOME':
                self.exitCommand = 'HOME'
                self.doClose()
        finally:
            del w

    def createGrandparentedListItem(self, obj, thumb_w, thumb_h):
        title = obj.grandparentTitle or obj.parentTitle or obj.title or ''
        titleSort = obj.titleSort or title
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli, titleSort

    def createParentedListItem(self, obj, thumb_w, thumb_h):
        title = obj.parentTitle or obj.title or ''
        titleSort = obj.titleSort or title
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli, titleSort

    def createSimpleListItem(self, obj, thumb_w, thumb_h):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli, obj.titleSort or obj.title

    def createListItem(self, obj):
        if obj.type == 'episode':
            mli, titleSort = self.createGrandparentedListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        elif obj.type == 'season':
            mli, titleSort = self.createParentedListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        elif obj.type == 'movie':
            mli, titleSort = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
        elif obj.type == 'show':
            mli, titleSort = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        elif obj.type == 'album':
            mli, titleSort = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
        elif obj.type == 'track':
            mli, titleSort = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
        elif obj.type == 'photo':
            mli, titleSort = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
        elif obj.type == 'clip':
            mli, titleSort = self.createSimpleListItem(obj, *self.THUMB_AR16X9_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie16x9.png')
        else:
            util.DEBUG_LOG('Unhandled item: {0}'.format(obj.type))
            return None, None

        return mli, titleSort

    def fillShows(self):
        items = []
        keys = []
        self.firstOfKeyItems = {}
        idx = 0
        for show in self.section.all():
            mli, titleSort = self.createListItem(show)
            if mli:
                mli.setProperty('index', str(idx))
                label = mli.getLabel()
                if titleSort in label:
                    key = titleSort[0].upper()
                else:
                    key = label[0].upper()
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
        for key in keys:
            mli = kodigui.ManagedListItem(key, data_source=key)
            mli.setProperty('key', key)
            self.keyItems[key] = mli
            litems.append(mli)

        self.showPanelControl.addItems(items)
        self.keyListControl.addItems(litems)

        self.setProperty('key', keys[0])
