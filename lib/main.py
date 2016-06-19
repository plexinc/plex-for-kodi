import threading
import xbmc
import plex
from plexnet import plexapp
from windows import background, userselect, home
import player
import backgroundthread
import util


def waitForThreads():
    util.DEBUG_LOG('Checking for any remaining threads')
    for t in threading.enumerate():
        if t != threading.currentThread():
            if t.isAlive():
                if isinstance(t, threading._Timer):
                    t.cancel()
                util.DEBUG_LOG('Waiting on: {0}...'.format(t.name))
                t.join()


def main():
    util.DEBUG_LOG('STARTED: {0}'.format(util.ADDON.getAddonInfo('version')))
    back = background.BackgroundWindow.create()
    background.setSplash()
    hw = None
    try:
        while not xbmc.abortRequested:
            if plex.init():
                background.setSplash(False)
                while not xbmc.abortRequested:
                    if len(plexapp.ACCOUNT.homeUsers) > 1 or plexapp.ACCOUNT.isProtected:
                        if not userselect.start():
                            return

                    try:
                        done = plex.CallbackEvent(plexapp.APP, 'change:selectedServer', timeout=11)
                        if not plexapp.SERVERMANAGER.selectedServer:
                            util.DEBUG_LOG('Waiting for selected server...')
                            try:
                                background.setBusy()
                                done.wait()
                            finally:
                                background.setBusy(False)

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
        player.PLAYER.close(shutdown=True)
        plexapp.APP.preShutdown()
        backgroundthread.BGThreader.shutdown()
        plexapp.APP.shutdown()
        waitForThreads()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back

        util.DEBUG_LOG('FINISHED')
