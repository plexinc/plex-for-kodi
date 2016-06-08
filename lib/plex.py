import platform
import uuid
import json
import threading
import time

import xbmc

from plexnet import plexapp, myplex
import util


class PlexTimer(plexapp.Timer):
    def shouldAbort(self):
        return xbmc.abortRequested


plexapp.setTimer(PlexTimer)


class PlexInterface(plexapp.AppInterface):
    _regs = {
        None: {},
    }
    _globals = {
        'platform': platform.uname()[0],
        'appVersionStr': util.ADDON.getAddonInfo('version'),
        'clientIdentifier': str(hex(uuid.getnode())),
        'platformVersion': platform.uname()[2],
        'product': 'Plex for Kodi',
        'provides': 'player',
        'device': plexapp._platform,
        'model': 'Unknown',
        'friendlyName': 'Kodi Plex Addon',
    }

    def getPreference(self, pref, default=None):
        return util.getSetting(pref, default)

    def setPreference(self, pref, value):
        util.setSetting(pref, value)

    def getRegistry(self, reg, default=None, sec=None):
        if sec == 'myplex' and reg == 'MyPlexAccount':
            ret = util.getSetting('{0}.{1}'.format(sec, reg), default)
            if ret:
                return ret
            return json.dumps({'authToken': util.getSetting('auth.token')})
        else:
            return util.getSetting('{0}.{1}'.format(sec, reg), default)

    def setRegistry(self, reg, value, sec=None):
        util.setSetting('{0}.{1}'.format(sec, reg), value)

    def clearRegistry(self, reg, sec=None):
        util.setSetting('{0}.{1}'.format(sec, reg), '')

    def addInitializer(self, sec):
        pass

    def clearInitializer(self, sec):
        pass

    def getGlobal(self, glbl, default=None):
        return self._globals.get(glbl, default)

    def getCapabilities(self):
        return ''

    def LOG(self, msg):
        util.DEBUG_LOG('API: {0}'.format(msg))

    def DEBUG_LOG(self, msg):
        self.LOG('DEBUG: {0}'.format(msg))

    def WARN_LOG(self, msg):
        self.LOG('WARNING: {0}'.format(msg))

    def ERROR(self, msg=None, err=None):
        if err:
            self.LOG('ERROR: {0} - {1}'.format(msg, err.message))
        else:
            util.ERROR()


plexapp.setInterface(PlexInterface())


class CallbackEvent(threading._Event):
    def __init__(self, context, signal, timeout=15, *args, **kwargs):
        threading._Event.__init__(self, *args, **kwargs)
        self.start = time.time()
        self.context = context
        self.signal = signal
        self.timeout = timeout
        self.context.on(self.signal, self.set)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.wait()

    def __del__(self):
        self.close()

    def __repr__(self):
        return '<{0}:{1}>'.format(self.__class__.__name__, self.signal)

    def set(self, **kwargs):
        threading._Event.set(self)

    def wait(self):
        if not threading._Event.wait(self, self.timeout):
            util.DEBUG_LOG('{0}: TIMED-OUT'.format(self))
        self.close()

    def triggeredOrTimedOut(self, timeout=None):
        try:
            if time.time() - self.start() > self.timeout:
                util.DEBUG_LOG('{0}: TIMED-OUT'.format(self))
                return True

            if timeout:
                threading._Event.wait(self, timeout)
        finally:
            return self.isSet()

    def close(self):
        self.set()
        self.context.off(self.signal, self.set)


def init():
    util.DEBUG_LOG('Initializing...')

    with CallbackEvent(plexapp.APP, 'init'):
        plexapp.init()
        util.DEBUG_LOG('Waiting for account initialization...')

    if not plexapp.ACCOUNT.authToken:
        token = authorize()

        if not token:
            util.DEBUG_LOG('FAILED TO AUTHORIZE')
            return False

        with CallbackEvent(plexapp.APP, 'account:response'):
            plexapp.ACCOUNT.validateToken(token)
            util.DEBUG_LOG('Waiting for account initialization...')

    # if not PLEX:
    #     util.messageDialog('Connection Error', u'Unable to connect to any servers')
    #     util.DEBUG_LOG('SIGN IN: Failed to connect to any servers')
    #     return False

    # util.DEBUG_LOG('SIGN IN: Connected to server: {0} - {1}'.format(PLEX.friendlyName, PLEX.baseuri))
    return True


def authorize():
    from windows import signin, background

    background.setSplash(False)

    back = signin.Background.create()

    pre = signin.PreSignInWindow.open()
    try:
        if not pre.doSignin:
            return None
    finally:
        del pre

    try:
        while True:
            pinLoginWindow = signin.PinLoginWindow.create()
            pl = myplex.PinLogin()
            pinLoginWindow.setPin(pl.pin)

            try:
                pl.startTokenPolling()
                while not pl.finished():
                    if pinLoginWindow.abort:
                        util.DEBUG_LOG('SIGN IN: Pin login aborted')
                        pl.abort()
                        return None
                    xbmc.sleep(100)
                else:
                    if not pl.expired():
                        if pl.authenticationToken:
                            pinLoginWindow.setLinking()
                            return pl.authenticationToken
                        else:
                            return None
            finally:
                pinLoginWindow.doClose()
                del pinLoginWindow

            if pl.expired():
                util.DEBUG_LOG('SIGN IN: Pin expired')
                expiredWindow = signin.ExpiredWindow.open()
                try:
                    if not expiredWindow.refresh:
                        util.DEBUG_LOG('SIGN IN: Pin refresh aborted')
                        return None
                finally:
                    del expiredWindow
    finally:
        back.doClose()
        del back
