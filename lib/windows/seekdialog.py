import kodigui
from lib import util


class SeekDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-seek_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    IMAGE_LIST_ID = 100
    SEEK_IMAGE_ID = 200
    BIF_IMAGE_ID = 300
    SEEK_IMAGE_WIDTH = 1600

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.handler = kwargs.get('handler')
        self.bifURL = None
        self.imageListControl = None
        self.baseOffset = 0
        self.duration = 0
        self.offset = 0
        self.imageListSize = 1

    def trueOffset(self):
        return self.baseOffset + self.offset

    def selectedOffset(self):
        return self.imageListControl.getSelectedItem().dataSource

    def onFirstInit(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.bifImageControl = self.getControl(self.BIF_IMAGE_ID)
        self.imageListControl = kodigui.ManagedControlList(self, self.IMAGE_LIST_ID, 6)
        self.setFocusId(self.IMAGE_LIST_ID)
        self.fillList()
        self.update()

    def onReInit(self):
        self.updateProgress()

    def onAction(self, action):
        try:
            self._updateProgress()
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.IMAGE_LIST_ID:
            self.handler.seek(self.selectedOffset())
            self.doClose()

    def setup(self, duration, offset=0, bif_url=None):
        self.baseOffset = offset
        self.offset = 0
        self.duration = duration
        self.bifURL = bif_url
        # self.getBif()
        if self.imageListControl:
            self.fillList()
            self.update()

    def update(self, offset=None):
        if offset is not None:
            self.offset = offset

        self.updateProgress()

    def updateProgress(self):
        if not self.imageListControl:
            return

        offset = self.trueOffset()
        for mli in self.imageListControl:
            if mli.dataSource > offset:
                pos = mli.pos()
                self.imageListControl.selectItem(pos and pos - 1 or 0)
                break

        # self.imageListControl.selectItem(int(((self.baseOffset + self.offset) / float(self.duration)) * int(self.imageListSize)))
        self._updateProgress()

    def _updateProgress(self):
        ratio = self.selectedOffset() / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        # bifx = (w - int(ratio * 320)) + 40
        bifx = w
        self.seekbarControl.setWidth(w)
        self.bifImageControl.setPosition(bifx, 600)

    def fillList(self):
        self.fillBlankList()

    def fillBlankList(self):
        items = []
        for x in range(self.duration / 10000):
            offset = x * 10000
            items.append(kodigui.ManagedListItem(thumbnailImage=self.bifURL.replace('0?', str(offset) + '?'), data_source=offset))
        self.imageListControl.addItems(items)

        self.imageListSize = float(self.imageListControl.size())
        util.DEBUG_LOG('Seek image count: {0}'.format(self.imageListSize))
