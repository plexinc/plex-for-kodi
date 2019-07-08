import contextlib
import kodigui
from lib import util


class PlayerBackground(kodigui.BaseWindow):
    xmlFile = 'script-plex-player_background.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.background = kwargs.get('background', '')
        self._closedSet = False

    def onFirstInit(self):
        self.setProperty('background', self.background)

    def onReInit(self):
        if self._closedSet:
            self._closedSet = False
            self.doClose()

    @contextlib.contextmanager
    def asContext(self):
        self.show()
        yield
        self.doClose()

    def setClosed(self):
        self._closedSet = True
        self.doClose()


class PlayerBackgroundContext(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.window = None

    def __enter__(self):
        self.window = PlayerBackground.create(**self.kwargs)

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self.window:
            self.window.doClose()
            del self.window
            self.window = None
