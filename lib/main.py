import xbmc
import plex
from plexnet import plexapp
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
                done = plex.CallbackEvent(plexapp.INTERFACE, 'change:selectedServer')

                while not xbmc.abortRequested:
                    if len(plexapp.ACCOUNT.homeUsers) > 1 or plexapp.ACCOUNT.isProtected:
                        background.setSplash(False)
                        if not userselect.start():
                            return
                    try:
                        if not plexapp.SERVERMANAGER.selectedServer:
                            util.DEBUG_LOG('Waiting for selected server')
                            done.wait()

                        hw = home.HomeWindow.open()

                        if not hw.closeOption:
                            return

                        if hw.closeOption == 'signout':
                            plexapp.ACCOUNT.signOut()
                            break
                    finally:
                        del hw
            else:
                break
    except:
        util.ERROR()
    finally:
        backgroundthread.BGThreader.shutdown()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back

        util.DEBUG_LOG('FINISHED')
