import kodigui

from lib import util


class ShowsWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-shows.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SHOW_PANEL_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.section = kwargs.get('section')

    def onFirstInit(self):
        self.showPanelControl = kodigui.ManagedControlList(self, self.SHOW_PANEL_ID, 5)
        self.fillShows()

    def createGrandparentedListItem(self, obj):
        title = obj.grandparentTitle or obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.thumbUrl, data_source=obj)
        return mli

    def createParentedListItem(self, obj):
        title = obj.parentTitle or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.thumbUrl, data_source=obj)
        return mli

    def createSimpleListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumbUrl, data_source=obj)
        return mli

    def createListItem(self, obj):
        if obj.type == 'episode':
            return self.createGrandparentedListItem(obj)
        elif obj.type == 'season':
            return self.createParentedListItem(obj)
        elif obj.type == 'movie':
            return self.createSimpleListItem(obj)
        elif obj.type == 'show':
            return self.createSimpleListItem(obj)
        elif obj.type == 'album':
            return self.createParentedListItem(obj)
        elif obj.type == 'track':
            return self.createParentedListItem(obj)
        elif obj.type == 'photo':
            return self.createSimpleListItem(obj)
        elif obj.type == 'clip':
            return self.createSimpleListItem(obj)

    def fillShows(self):
        items = []
        for show in self.section.all():
            mli = self.createListItem(show)
            if mli:
                items.append(mli)

        self.showPanelControl.addItems(items)
