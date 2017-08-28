import sys
import platform
import uuid
import json
import threading
import time
import requests

import xbmc

from plexnet import plexapp, myplex
import util


class PlexTimer(plexapp.Timer):
    def shouldAbort(self):
        return xbmc.abortRequested


def abortFlag():
    return util.MONITOR.abortRequested()


plexapp.setTimer(PlexTimer)
plexapp.setAbortFlagFunction(abortFlag)

maxVideoRes = plexapp.Res((3840, 2160))  # INTERFACE.globals["supports4k"] and plexapp.Res((3840, 2160)) or plexapp.Res((1920, 1080))

CLIENT_ID = util.getSetting('client.ID')
if not CLIENT_ID:
    CLIENT_ID = str(uuid.uuid4())
    util.setSetting('client.ID', CLIENT_ID)


def defaultUserAgent():
    """Return a string representing the default user agent."""
    _implementation = platform.python_implementation()

    if _implementation == 'CPython':
        _implementation_version = platform.python_version()
    elif _implementation == 'PyPy':
        _implementation_version = '%s.%s.%s' % (sys.pypy_version_info.major,
                                                sys.pypy_version_info.minor,
                                                sys.pypy_version_info.micro)
        if sys.pypy_version_info.releaselevel != 'final':
            _implementation_version = ''.join([_implementation_version, sys.pypy_version_info.releaselevel])
    elif _implementation == 'Jython':
        _implementation_version = platform.python_version()  # Complete Guess
    elif _implementation == 'IronPython':
        _implementation_version = platform.python_version()  # Complete Guess
    else:
        _implementation_version = 'Unknown'

    try:
        p_system = platform.system()
        p_release = platform.release()
    except IOError:
        p_system = 'Unknown'
        p_release = 'Unknown'

    return " ".join(['%s/%s' % ('Plex-for-Kodi', util.ADDON.getAddonInfo('version')),
                     '%s/%s' % ('Kodi', xbmc.getInfoLabel('System.BuildVersion').replace(' ', '-')),
                     '%s/%s' % (_implementation, _implementation_version),
                     '%s/%s' % (p_system, p_release)])


class PlexInterface(plexapp.AppInterface):
    _regs = {
        None: {},
    }
    _globals = {
        'platform': platform.uname()[0],
        'appVersionStr': util.ADDON.getAddonInfo('version'),
        'clientIdentifier': CLIENT_ID,
        'platformVersion': platform.uname()[2],
        'product': 'Plex for Kodi',
        'provides': 'player',
        'device': plexapp._platform,
        'model': 'Unknown',
        'friendlyName': 'Kodi Add-on ({0})'.format(platform.node()),
        'supports1080p60': True,
        'vp9Support': True,
        'transcodeVideoQualities': [
            "10", "20", "30", "30", "40", "60", "60", "75", "100", "60", "75", "90", "100", "100"
        ],
        'transcodeVideoResolutions': [
            plexapp.Res((220, 180)),
            plexapp.Res((220, 128)),
            plexapp.Res((284, 160)),
            plexapp.Res((420, 240)),
            plexapp.Res((576, 320)),
            plexapp.Res((720, 480)),
            plexapp.Res((1024, 768)),
            plexapp.Res((1280, 720)),
            plexapp.Res((1280, 720)),
            maxVideoRes, maxVideoRes, maxVideoRes, maxVideoRes, maxVideoRes
        ],
        'transcodeVideoBitrates': [
            "64", "96", "208", "320", "720", "1500", "2000", "3000", "4000", "8000", "10000", "12000", "20000", "200000"
        ],
        'deviceInfo': plexapp.DeviceInfo()
    }

    def getPreference(self, pref, default=None):
        if pref == 'manual_connections':
            return self.getManualConnections()
        else:
            return util.getSetting(pref, default)

    def getManualConnections(self):
        conns = []
        for i in range(2):
            ip = util.getSetting('manual_ip_{0}'.format(i))
            if not ip:
                continue
            port = util.getSetting('manual_port_{0}'.format(i), 32400)
            conns.append({'connection': ip, 'port': port})
        return json.dumps(conns)

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
        if glbl == 'transcodeVideoResolutions':
            maxres = self.getPreference('allow_4k', True) and plexapp.Res((3840, 2160)) or plexapp.Res((1920, 1080))
            self._globals['transcodeVideoResolutions'][-5:] = [maxres] * 5
        return self._globals.get(glbl, default)

    def getCapabilities(self):
        return ''

    def LOG(self, msg):
        util.DEBUG_LOG('API: {0}'.format(msg))

    def DEBUG_LOG(self, msg):
        self.LOG('DEBUG: {0}'.format(msg))

    def WARN_LOG(self, msg):
        self.LOG('WARNING: {0}'.format(msg))

    def ERROR_LOG(self, msg):
        self.LOG('ERROR: {0}'.format(msg))

    def ERROR(self, msg=None, err=None):
        if err:
            self.LOG('ERROR: {0} - {1}'.format(msg, err.message))
        else:
            util.ERROR()

    def supportsAudioStream(self, codec, channels):
        return True
        # if codec = invalid then return true

        # canDownmix = (m.globals["audioDownmix"][codec] <> invalid)
        # supportsSurroundSound = m.SupportsSurroundSound()

        # if not supportsSurroundSound and canDownmix then
        #     maxChannels = m.globals["audioDownmix"][codec]
        # else
        #     maxChannels = firstOf(m.globals["audioDecoders"][codec], 0)
        # end if

        # if maxChannels > 2 and not canDownmix and not supportsSurroundSound then
        #     ' It's a surround sound codec and we can't do surround sound
        #     supported = false
        # else if maxChannels = 0 or maxChannels < channels then
        #     ' The codec is either unsupported or can't handle the requested channels
        #     supported = false
        # else
        #     supported = true

        # return supported

    def supportsSurroundSound(self):
        return True

    def getQualityIndex(self, qualityType):
        if qualityType == self.QUALITY_LOCAL:
            return self.getPreference("local_quality", 13)
        elif qualityType == self.QUALITY_ONLINE:
            return self.getPreference("online_quality", 8)
        else:
            return self.getPreference("remote_quality", 13)

    def getMaxResolution(self, quality_type, allow4k=False):
        qualityIndex = self.getQualityIndex(quality_type)

        if qualityIndex >= 9:
            if self.getPreference('allow_4k', True):
                return allow4k and 2160 or 1088
            else:
                return 1088
        elif qualityIndex >= 6:
            return 720
        elif qualityIndex >= 5:
            return 480
        else:
            return 360


plexapp.setInterface(PlexInterface())
plexapp.setUserAgent(defaultUserAgent())


class CallbackEvent(plexapp.CompatEvent):
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

    retry = True

    while retry:
        retry = False
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
        success = requirePlexPass()
        if success == 'RETRY':
            retry = True
            continue

        return success


def requirePlexPass():
    return True
    # if not plexapp.ACCOUNT.hasPlexPass():
    #     from windows import signin, background
    #     background.setSplash(False)
    #     w = signin.SignInPlexPass.open()
    #     retry = w.retry
    #     del w
    #     util.DEBUG_LOG('PlexPass required. Signing out...')
    #     plexapp.ACCOUNT.signOut()
    #     plexapp.SERVERMANAGER.clearState()
    #     if retry:
    #         return 'RETRY'
    #     else:
    #         return False

    # return True


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
            try:
                pl = myplex.PinLogin()
            except requests.ConnectionError:
                util.ERROR()
                util.messageDialog(util.T(32427, 'Failed'), util.T(32449, 'Sign-in failed. Cound not connect to plex.tv'))
                return

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
