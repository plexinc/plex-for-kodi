import kodigui

from lib import colors
from lib import util

import episodes


class SeasonsWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-seasons.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_POSTER_DIM = (250, 370)

    SEASON_LIST_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.show = kwargs.get('show')
        self.exitCommand = None

    def onFirstInit(self):
        self.seasonListControl = kodigui.ManagedControlList(self, self.SEASON_LIST_ID, 5)
        self.setProperty('summary', self.show.summary)
        self.setProperty('thumb', self.show.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
        self.setProperty('background', self.show.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))

        self.fillSeasons()
        self.setFocusId(self.SEASON_LIST_ID)

    # def onAction(self, action):
    #     try:
    #         if action == xbmcgui.ACTION_NAV_BACK:
    #             if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
    #                 self.setFocusId(self.OPTIONS_GROUP_ID)
    #                 return

    #     except:
    #         util.ERROR()

    #     kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.exitCommand = 'HOME'
            self.doClose()
        elif controlID == self.SEASON_LIST_ID:
            self.seasonListClicked()

    def seasonListClicked(self):
        mli = self.seasonListControl.getSelectedItem()
        if not mli:
            return

        w = episodes.EpisodesWindow.open(season=mli.dataSource)
        try:
            if w.exitCommand == 'HOME':
                self.exitCommand = 'HOME'
                self.doClose()
        finally:
            del w

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM), data_source=obj)
        return mli

    def fillSeasons(self):
        items = []
        idx = 0
        for season in self.show.seasons():
            mli = self.createListItem(season)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.seasonListControl.addItems(items)
