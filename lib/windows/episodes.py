import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util

import preplay


class EpisodesWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-episodes.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_AR16X9_DIM = (619, 348)

    EPISODE_PANEL_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.season = kwargs.get('season')
        self.exitCommand = None

    def onFirstInit(self):
        self.episodePanelControl = kodigui.ManagedControlList(self, self.EPISODE_PANEL_ID, 5)

        self.setProperty(
            'background', self.season.show().art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.fillEpisodes()
        self.setFocusId(self.EPISODE_PANEL_ID)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
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
        elif controlID == self.EPISODE_PANEL_ID:
            self.episodePanelClicked()

    def episodePanelClicked(self):
        mli = self.episodePanelControl.getSelectedItem()
        if not mli:
            return

        w = preplay.PrePlayWindow.open(video=mli.dataSource)
        try:
            if w.exitCommand == 'HOME':
                self.exitCommand = 'HOME'
                self.doClose()
        finally:
            del w

    def createListItem(self, obj):
        title = obj.index and 'Episode {0}'.format(obj.index) or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM), data_source=obj)
        return mli

    def fillEpisodes(self):
        items = []
        idx = 0
        for episode in self.season.episodes():
            mli = self.createListItem(episode)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.episodePanelControl.addItems(items)
