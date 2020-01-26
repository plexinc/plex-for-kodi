import xbmc

from lib import plex, util

from lib.windows import slidehshow

class ScreensaverMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()

def main():
    util.DEBUG_LOG("[SS] Starting")
    if plex.init():
        with util.Cron(1):
            ss = slidehshow.Slideshow.create()
            ss.monitor = ScreensaverMonitor(action = ss.close)
            ss.modal()
            del ss

if __name__ == '__main__':
    main()