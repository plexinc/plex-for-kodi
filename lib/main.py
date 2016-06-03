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
                background.setSplash(False)
                while not xbmc.abortRequested:
                    if len(plexapp.ACCOUNT.homeUsers) > 1 or plexapp.ACCOUNT.isProtected:
                        if not userselect.start():
                            return

                    try:
                        done = plex.CallbackEvent(plexapp.APP, 'change:selectedServer')
                        if not plexapp.SERVERMANAGER.selectedServer:
                            util.DEBUG_LOG('Waiting for selected server...')
                            done.wait()

                        util.DEBUG_LOG('STARTING WITH SERVER: {0}'.format(plexapp.SERVERMANAGER.selectedServer))

                        hw = home.HomeWindow.open()

                        if not hw.closeOption:
                            return

                        if hw.closeOption == 'signout':
                            util.setSetting('auth.token', '')
                            util.DEBUG_LOG('Signing out...')
                            plexapp.ACCOUNT.signOut()
                            break
                    finally:
                        del hw
            else:
                break
    except:
        util.ERROR()
    finally:
        plexapp.APP.preShutdown()
        backgroundthread.BGThreader.shutdown()
        plexapp.APP.shutdown()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back

        util.DEBUG_LOG('FINISHED')
