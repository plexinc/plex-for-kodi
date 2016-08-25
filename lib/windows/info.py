import kodigui
from lib import util


class InfoWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-info.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_DIM_POSTER = (519, 469)
    THUMB_DIM_SQUARE = (519, 519)

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.title = kwargs.get('title')
        self.subTitle = kwargs.get('sub_title')
        self.thumb = kwargs.get('thumb')
        self.info = kwargs.get('info')
        self.background = kwargs.get('background')
        self.isSquare = kwargs.get('is_square')
        self.thumbDim = self.isSquare and self.THUMB_DIM_SQUARE or self.THUMB_DIM_POSTER

    def onFirstInit(self):
        self.setProperty('is.square', self.isSquare and '1' or '')
        self.setProperty('title.main', self.title)
        self.setProperty('title.sub', self.subTitle)
        self.setProperty('thumb', self.thumb.asTranscodedImageURL(*self.thumbDim))
        self.setProperty('info', self.info)
        self.setProperty('background', self.background)
