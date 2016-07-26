import kodigui
from lib import util

util.setGlobalProperty('background.busy', '')
util.setGlobalProperty('background.shutdown', '')


class BackgroundWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-background.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080


def setBusy(on=True):
    util.setGlobalProperty('background.busy', on and '1' or '')


def setSplash(on=True):
    util.setGlobalProperty('background.splash', on and '1' or '')


def setShutdown(on=True):
    util.setGlobalProperty('background.shutdown', on and '1' or '')
