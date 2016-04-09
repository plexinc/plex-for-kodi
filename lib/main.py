import plex
from windows import background, userselect, home
import backgroundthread
import util


def main():
    util.DEBUG_LOG('STARTED: {0}'.format(util.ADDON.getAddonInfo('version')))
    back = background.BackgroundWindow.create()
    background.setSplash()

    try:
        if plex.init():
            if plex.PLEX.multiuser:
                background.setSplash(False)
                user, pin = userselect.getUser()
                if not user:
                    return
                background.setBusy()
                plex.switchUser(user, pin)

            home.HomeWindow.open()
    finally:
        backgroundthread.BGThreader.shutdown()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back

    util.DEBUG_LOG('FINISHED')
