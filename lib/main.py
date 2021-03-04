from __future__ import absolute_import
from kodi_six import xbmc

from ._included_packages.plexnet.gdmClient import GDMClientDiscovery
from ._included_packages.plexnet.httpServer import HttpServer

if xbmc.getInfoLabel('Window(10000).Property(script.plex.running)') == "1":
    command = 'XBMC.NotifyAll({0},{1},{2})'.format('script.plex', 'RESTORE', None)
    xbmc.executebuiltin(command)
    raise SystemExit

import gc
import atexit
import threading
import six

from . import plex

from plexnet import plexapp
from plexnet import threadutils
from .windows import background, userselect, home, windowutils
from . import player
from . import backgroundthread
from . import util


BACKGROUND = None


if six.PY2:
    _Timer = threading._Timer
else:
    _Timer = threading.Timer


def waitForThreads():
    util.DEBUG_LOG('Main: Checking for any remaining threads')
    while len(threading.enumerate()) > 1:
        for t in threading.enumerate():
            if t != threading.currentThread():
                if t.isAlive():
                    util.DEBUG_LOG('Main: Waiting on: {0}...'.format(t.name))
                    if isinstance(t, _Timer):
                        t.cancel()

                    try:
                        t.join()
                    except:
                        util.ERROR()


@atexit.register
def realExit():
    xbmc.log('Main: script.plex: REALLY FINISHED', xbmc.LOGINFO)


def signout():
    util.setSetting('auth.token', '')
    util.DEBUG_LOG('Main: Signing out...')
    plexapp.ACCOUNT.signOut()


def main():
    global BACKGROUND
    util.setGlobalProperty('running', '1')
    try:
        with util.Cron(1):
            BACKGROUND = background.BackgroundWindow.create(function=_main)
            BACKGROUND.modal()
            del BACKGROUND
    finally:
        util.setGlobalProperty('running', '')


def _main():
    util.DEBUG_LOG('[ STARTED: {0} -------------------------------------------------------------------- ]'.format(util.ADDON.getAddonInfo('version')))
    util.DEBUG_LOG('USER-AGENT: {0}'.format(plex.defaultUserAgent()))
    background.setSplash()

    gdmClient = GDMClientDiscovery()
    gdmClient.discover()
    httpServer = HttpServer()
    httpServer.start()

    try:
        while not util.MONITOR.abortRequested():
            if plex.init():
                background.setSplash(False)
                while not util.MONITOR.abortRequested():
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
                                    plex.CallbackEvent(plexapp.util.APP, 'change:selectedServer', timeout=timeout).wait()

                                    selectedServer = plexapp.SERVERMANAGER.checkSelectedServerSearch(skip_preferred=skip_preferred, skip_owned=skip_owned)
                                    if selectedServer:
                                        break
                                else:
                                    util.DEBUG_LOG('Main: Finished waiting for selected server...')
                            finally:
                                background.setBusy(False)

                        util.DEBUG_LOG('Main: STARTING WITH SERVER: {0}'.format(selectedServer))

                        windowutils.HOME = home.HomeWindow.open()
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
                        BACKGROUND.activate()
                        gc.collect(2)

            else:
                break
    except:
        util.ERROR()
    finally:
        util.DEBUG_LOG('Main: SHUTTING DOWN...')
        background.setShutdown()
        player.shutdown()
        plexapp.util.APP.preShutdown()
        util.CRON.stop()
        backgroundthread.BGThreader.shutdown()
        plexapp.util.APP.shutdown()
        waitForThreads()
        background.setBusy(False)
        background.setSplash(False)
        gdmClient.close()
        httpServer.close()

        util.DEBUG_LOG('FINISHED')

        from .windows import kodigui
        kodigui.MONITOR = None
        util.shutdown()

        gc.collect(2)
