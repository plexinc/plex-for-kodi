import xbmc
import plex
from windows import background, userselect, home
import backgroundthread
import util


def main():
    util.DEBUG_LOG('STARTED: {0}'.format(util.ADDON.getAddonInfo('version')))
    back = background.BackgroundWindow.create()
    background.setSplash()
    try:
        while not xbmc.abortRequested:
            if plex.init():
                while not xbmc.abortRequested:
                    if plex.BASE.multiuser and plex.BASE.owned:
                        background.setSplash(False)
                        user, pin = userselect.getUser()
                        if not user:
                            return
                        background.setBusy()
                        plex.switchUser(user, pin)
                    else:
                        plex.initSingleUser()

                    try:
                        hw = home.HomeWindow.open()

                        if not hw.closeOption:
                            return

                        if hw.closeOption == 'signout':
                            plex.signOut()
                            break
                    finally:
                        del hw
            else:
                break
    except:
        util.ERROR()
    finally:
        plex.SEVERMANAGER and plex.SEVERMANAGER.abort()
        backgroundthread.BGThreader.shutdown()
        plex.SEVERMANAGER and plex.SEVERMANAGER.finish()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back

        util.DEBUG_LOG('FINISHED')
