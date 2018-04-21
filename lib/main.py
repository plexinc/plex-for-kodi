import gc
import atexit
import threading

import xbmc
import plex

from plexnet import plexapp
from plexnet import threadutils
from windows import background, userselect, home, windowutils
import player
import backgroundthread
import util


BACKGROUND = None


def waitForThreads():
    util.DEBUG_LOG('Main: Checking for any remaining threads')
    while len(threading.enumerate()) > 1:
        for t in threading.enumerate():
            if t != threading.currentThread():
                if t.isAlive():
                    util.DEBUG_LOG('Main: Waiting on: {0}...'.format(t.name))
                    if isinstance(t, threading._Timer):
                        t.cancel()
                        t.join()
                    elif isinstance(t, threadutils.KillableThread):
                        t.kill(force_and_wait=True)
                    else:
                        t.join()


@atexit.register
def realExit():
    xbmc.log('Main: script.plex: REALLY FINISHED', xbmc.LOGNOTICE)


def signout():
    util.setSetting('auth.token', '')
    util.DEBUG_LOG('Main: Signing out...')
    plexapp.ACCOUNT.signOut()


def main():
    global BACKGROUND
    util.setGlobalProperty('running', '1')
    util.setGlobalProperty('silent_shutdown', '')
    try:
        with util.Cron(1):
            BACKGROUND = background.BackgroundWindow.create(function=_main)
            BACKGROUND.modal()
            del BACKGROUND
    finally:
        util.setGlobalProperty('running', '')
        util.setGlobalProperty('silent_shutdown', '')


def _main():
    util.DEBUG_LOG('[ STARTED: {0} -------------------------------------------------------------------- ]'.format(util.ADDON.getAddonInfo('version')))
    util.DEBUG_LOG('USER-AGENT: {0}'.format(plex.defaultUserAgent()))
    background.setSplash()
    silent_shutdown = False

    try:
        while not xbmc.abortRequested:
            if plex.init():
                background.setSplash(False)
                while not xbmc.abortRequested:
                    if (
                        not plexapp.ACCOUNT.isOffline and not
                        plexapp.ACCOUNT.isAuthenticated and
                        (len(plexapp.ACCOUNT.homeUsers) > 1 or plexapp.ACCOUNT.isProtected)

                    ):
                        result = userselect.start()
                        if not result:
                            return
                        elif result == 'signout':
                            signout()
                            break
                        elif result == 'signin':
                            break
                        util.DEBUG_LOG('Main: User selected')

                    try:
                        selectedServer = plexapp.SERVERMANAGER.selectedServer

                        if not selectedServer:
                            background.setBusy()
                            util.DEBUG_LOG('Main: Waiting for selected server...')
                            try:
                                for timeout, skip_preferred, skip_owned in ((10, True, False), (10, True, True)):
                                    plex.CallbackEvent(plexapp.APP, 'change:selectedServer', timeout=timeout).wait()

                                    selectedServer = plexapp.SERVERMANAGER.checkSelectedServerSearch(skip_preferred=skip_preferred, skip_owned=skip_owned)
                                    if selectedServer:
                                        break
                                else:
                                    util.DEBUG_LOG('Main: Finished waiting for selected server...')
                            finally:
                                background.setBusy(False)

                        util.DEBUG_LOG('Main: STARTING WITH SERVER: {0}'.format(selectedServer))

                        windowutils.HOME = home.HomeWindow.open()
                        silent_shutdown = util.getGlobalProperty('silent_shutdown') == "1" or False
                        util.CRON.cancelReceiver(windowutils.HOME)

                        if not windowutils.HOME.closeOption:
                            return

                        closeOption = windowutils.HOME.closeOption

                        windowutils.shutdownHome()

                        if closeOption == 'signout':
                            signout()
                            break
                        elif closeOption == 'switch':
                            plexapp.ACCOUNT.isAuthenticated = False
                    finally:
                        windowutils.shutdownHome()
                        if not silent_shutdown:
                            BACKGROUND.activate()
                        gc.collect(2)

            else:
                break
    except:
        util.ERROR()
    finally:
        util.DEBUG_LOG('Main: SHUTTING DOWN...')
        if silent_shutdown and BACKGROUND:
            BACKGROUND.doClose()

        if not silent_shutdown:
            background.setShutdown()
        player.shutdown()
        plexapp.APP.preShutdown()
        util.CRON.stop()
        backgroundthread.BGThreader.shutdown()
        plexapp.APP.shutdown()
        waitForThreads()
        if not silent_shutdown:
            background.setBusy(False)
            background.setSplash(False)

        util.DEBUG_LOG('FINISHED')

        from windows import kodigui
        kodigui.MONITOR = None
        util.shutdown()

        gc.collect(2)
