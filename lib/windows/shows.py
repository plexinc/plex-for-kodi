import kodigui

from lib import util


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

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.section = kwargs.get('section')

    def onFirstInit(self):
        self.showPanelControl = kodigui.ManagedControlList(self, self.SHOW_PANEL_ID, 5)
        self.fillShows()

    def createGrandparentedListItem(self, obj, thumb_w, thumb_h):
        title = obj.grandparentTitle or obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.transcodedThumbURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createParentedListItem(self, obj, thumb_w, thumb_h):
        title = obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.transcodedThumbURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createSimpleListItem(self, obj, thumb_w, thumb_h):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.transcodedThumbURL(thumb_w, thumb_h), data_source=obj)
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
            mli = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        elif obj.type == 'track':
            mli = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
            return mli
        elif obj.type == 'photo':
            mli = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
            return mli
        elif obj.type == 'clip':
            mli = self.createSimpleListItem(obj, *self.THUMB_AR16X9_DIM)
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie16x9.png')
            return mli
        else:
            util.DEBUG_LOG('Unhandled Hub item: {0}'.format(obj.type))

    def fillShows(self):
        items = []
        idx = 0
        for show in self.section.all():
            mli = self.createListItem(show)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.showPanelControl.addItems(items)
