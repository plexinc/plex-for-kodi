import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util

import episodes


class ShowWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-seasons.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_DIMS = {
        'show': {
            'main.thumb': (300, 444),
            'item.thumb': (250, 370)
        },
        'artist': {
            'main.thumb': (519, 519),
            'item.thumb': (215, 215)
        }
    }

    SUB_ITEM_LIST_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.mediaItem = kwargs.get('media_item')
        self.exitCommand = None

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)
        self.setProperty('summary', self.mediaItem.summary)
        self.setProperty('thumb', self.mediaItem.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['main.thumb']))
        self.setProperty(
            'background',
            self.mediaItem.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )

        self.fill()
        self.setFocusId(self.SUB_ITEM_LIST_ID)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return

        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.exitCommand = 'HOME'
            self.doClose()
        elif controlID == self.SUB_ITEM_LIST_ID:
            self.subItemListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()

    def subItemListClicked(self):
        mli = self.subItemListControl.getSelectedItem()
        if not mli:
            return

        if self.mediaItem.type == 'show':
            w = episodes.EpisodesWindow.open(season=mli.dataSource, show=self.mediaItem)
        elif self.mediaItem.type == 'artist':
            w = episodes.AlbumWindow.open(season=mli.dataSource, show=self.mediaItem)

        try:
            if w.exitCommand == 'HOME':
                self.exitCommand = 'HOME'
                self.doClose()
        finally:
            del w

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(
            obj.title or '',
            thumbnailImage=obj.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['item.thumb']),
            data_source=obj
        )
        return mli

    def fill(self):
        items = []
        idx = 0
        for season in self.mediaItem.seasons():
            mli = self.createListItem(season)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.subItemListControl.addItems(items)

    def showAudioPlayer(self):
        import musicplayer
        w = musicplayer.MusicPlayerWindow.open()
        del w


class ArtistWindow(ShowWindow):
    xmlFile = 'script-plex-artist.xml'

    def fill(self):
        self.mediaItem.reload()
        self.setProperty('artist.title', self.mediaItem.title)
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])
        self.setProperty('artist.genre', genres)
        items = []
        idx = 0
        for album in sorted(self.mediaItem.albums(), key=lambda x: x.year):
            mli = self.createListItem(album)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('year', album.year)
                items.append(mli)
                idx += 1

        self.subItemListControl.addItems(items)
