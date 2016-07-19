import xbmcgui
import kodigui
from lib import util
from plexnet import plexplayer


class PhotoWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-photo.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.photo = kwargs.get('photo')

    def onFirstInit(self):
        self.setProperties()

    def onAction(self, action):
        try:
            # controlID = self.getFocusId()
            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def setProperties(self):
        pobj = plexplayer.PlexPhotoPlayer(self.photo)
        meta = pobj.build()
        self.setProperty('photo', meta.get('url', ''))
