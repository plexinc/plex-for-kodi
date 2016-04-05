import xbmcgui
import kodigui
from lib import util
from lib import image


class Background(kodigui.BaseWindow):
    xmlFile = 'script-plex-signin_background.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080


class PreSignInWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-pre_signin.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SIGNIN_BUTTON_ID = 100

    def __init__(self, *args, **kwargs):
        self.doSignin = False
        kodigui.BaseWindow.__init__(self, *args, **kwargs)

    def onFirstInit(self):
        self.signinButton = self.getControl(self.SIGNIN_BUTTON_ID)

    def onClick(self, controlID):
        if controlID == self.SIGNIN_BUTTON_ID:
            self.doSignin = True
            self.doClose()


class PinLoginWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-pin_login.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        self.abort = False
        kodigui.BaseWindow.__init__(self, *args, **kwargs)

    def setPin(self, pin):
        pinImage = image.textToImage(' '.join(list(pin)))
        if pinImage:
            self.setProperty('pin.image', pinImage)
        else:
            self.setProperty('pin', pin)

    def setLinking(self):
        self.setProperty('linking', '1')
        self.setProperty('pin', '')
        self.setProperty('pin.image', '')

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                self.abort = True
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)


class ExpiredWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-refresh_code.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    REFRESH_BUTTON_ID = 100

    def __init__(self, *args, **kwargs):
        self.refresh = False
        kodigui.BaseWindow.__init__(self, *args, **kwargs)

    def onFirstInit(self):
        self.refreshButton = self.getControl(self.REFRESH_BUTTON_ID)

    def onClick(self, controlID):
        if controlID == self.REFRESH_BUTTON_ID:
            self.refresh = True
            self.doClose()
