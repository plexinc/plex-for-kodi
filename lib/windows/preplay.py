import xbmc
import xbmcgui
import kodigui

from lib import util


class PrePlayWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-pre_play.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_POSTER_DIM = (347, 518)

    EXTRA_LIST_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.exitCommand = None

    def onFirstInit(self):
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.setProperty('summary', self.video.summary)
        self.setProperty('thumb', self.video.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))

        self.fillExtras()
        self.setFocusId(self.EXTRA_LIST_ID)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_NAV_BACK:
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
        elif controlID == self.EXTRA_LIST_ID:
            self.extrasListClicked()

    def extrasListClicked(self):
        mli = self.seasonListControl.getSelectedItem()
        if not mli:
            return

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM), data_source=obj)
        return mli

    def fillExtras(self):
        return
        items = []
        idx = 0
        for extra in self.video.extras():
            mli = self.createListItem(extra)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.extraListControl.addItems(items)
