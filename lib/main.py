import sys
import threading
import xbmc
import plex
from plexnet import plexapp
from plexnet import threadutils
from windows import background, userselect, home
import player
import backgroundthread
import util


def waitForThreads():
    util.DEBUG_LOG('Checking for any remaining threads')
    for t in threading.enumerate():
        if t != threading.currentThread():
            if t.isAlive():
                util.DEBUG_LOG('Waiting on: {0}...'.format(t.name))
                if isinstance(t, threading._Timer):
                    t.cancel()
                    t.join()
                elif isinstance(t, threadutils.KillableThread):
                    t.kill(force_and_wait=True)
                else:
                    t.join()


def main():
    with util.Cron(5):
        _main()


def _main():
    util.DEBUG_LOG('STARTED: {0}'.format(util.ADDON.getAddonInfo('version')))
    back = background.BackgroundWindow.create()
    background.setSplash()

    try:
        while not xbmc.abortRequested:
            if plex.init():
                background.setSplash(False)
                tries = 0
                while not xbmc.abortRequested:
                    if not plexapp.ACCOUNT.isAuthenticated and (len(plexapp.ACCOUNT.homeUsers) > 1 or plexapp.ACCOUNT.isProtected):
                        if not userselect.start():
                            return

                    hw = None
                    try:
                        done = plex.CallbackEvent(plexapp.APP, 'change:selectedServer', timeout=11)
                        if not plexapp.SERVERMANAGER.selectedServer:
                            util.DEBUG_LOG('Waiting for selected server...')
                            try:
                                background.setBusy()
                                done.wait()
                            finally:
                                background.setBusy(False)

                        tries += 1
                        if not plexapp.SERVERMANAGER.selectedServer and tries <= 1:
                            util.DEBUG_LOG('No servers found. Waiting for selected server one more time...')
                            continue

                        util.DEBUG_LOG('STARTING WITH SERVER: {0}'.format(plexapp.SERVERMANAGER.selectedServer))

                        hw = home.HomeWindow.open()

                        if not hw.closeOption:
                            return

                        if hw.closeOption == 'signout':
                            util.setSetting('auth.token', '')
                            util.DEBUG_LOG('Signing out...')
                            plexapp.ACCOUNT.signOut()
                            break
                        elif hw.closeOption == 'switch':
                            plexapp.ACCOUNT.isAuthenticated = False
                    finally:
                        del hw
            else:
                break
    except:
        util.ERROR()
    finally:
        util.DEBUG_LOG('SHUTTING DOWN...')
        background.setShutdown()
        player.shutdown()
        plexapp.APP.preShutdown()
        util.CRON.stop()
        backgroundthread.BGThreader.shutdown()
        plexapp.APP.shutdown()
        waitForThreads()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back

        util.DEBUG_LOG('FINISHED')

        util.shutdown()

        import gc
        gc.collect(2)

        sys.exit()
