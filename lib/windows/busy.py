import kodigui
from lib import util


class BusyWindow(kodigui.BaseDialog):
    xmlFile = 'script-plex-busy.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080


def dialog(msg='LOADING'):
    def methodWrap(func):
        def inner(*args, **kwargs):
            w = BusyWindow.create()
            try:
                return func(*args, **kwargs)
            finally:
                w.doClose()
                del w
                util.garbageCollect()
        return inner
    return methodWrap


def widthDialog(method, msg, *args, **kwargs):
    return dialog(msg or 'LOADING')(method)(*args, **kwargs)
