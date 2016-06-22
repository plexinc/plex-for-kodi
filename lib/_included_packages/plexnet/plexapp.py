import threading
import platform
import uuid
import sys

import signalsmixin
import util

Res = util.Res

APP = None
INTERFACE = None

MANAGER = None
SERVERMANAGER = None
ACCOUNT = None


def init():
    global MANAGER, SERVERMANAGER, ACCOUNT
    import myplexaccount
    ACCOUNT = myplexaccount.ACCOUNT
    import plexservermanager
    SERVERMANAGER = plexservermanager.MANAGER
    import myplexmanager
    MANAGER = myplexmanager.MANAGER
    ACCOUNT.init()


class App(signalsmixin.SignalsMixin):
    def __init__(self):
        signalsmixin.SignalsMixin.__init__(self)
        self.pendingRequests = {}
        self.initializers = {}
        self.timers = []

    def addTimer(self, timer):
        self.timers.append(timer)

    def startRequest(self, request, context, body=None, contentType=None):
        context.request = request

        started = request.startAsync(body, contentType, context)

        if started:
            id = request.getIdentity()
            self.pendingRequests[id] = context

            # if context.timeout:
            #     timer = createTimer(context.timeout, callback.Callable(self.onRequestTimeout, context=context))
            #     self.addTimer(timer)
        elif context.callback:
            context.callback(None, context)

        return started

    def onRequestTimeout(self, context):
        requestContext = context
        request = requestContext.request
        requestID = request.getIdentity()

        request.cancel()
        del self.pendingRequests[requestID]

        util.WARN_LOG("Request to {0} timed out after {1} ms".format(request.url, requestContext.timeout))

        if requestContext.callback:
            requestContext.callback(None, requestContext)

    def addInitializer(self, name):
        self.initializers[name] = True

    def clearInitializer(self, name):
        if name in self.initializers:
            del self.initializers[name]
            if self.isInitialized():
                self.onInitialized()

    def isInitialized(self):
        return not self.initializers

    def onInitialized(self):
        # Wire up a few of our own listeners
        # PlexServerManager()
        # self.on("change:user", callback.Callable(self.onAccountChange))

        self.trigger('init')

    def cancelAllTimers(self):
        for timer in self.timers:
            timer.cancel()

    def preShutdown(self):
        if self.timers:
            util.DEBUG_LOG('Canceling App() timers')
            self.cancelAllTimers()

    def shutdown(self):
        if self.timers:
            util.DEBUG_LOG('Waiting for App() timers: Started')

            self.cancelAllTimers()

            for timer in self.timers:
                timer.join()

            util.DEBUG_LOG('Waiting for App() timers: Finished')


try:
    _platform = platform.platform()
except:
    try:
        _platform = platform.platform(terse=True)
    except:
        _platform = sys.platform


class DeviceInfo(object):
    def getCaptionsOption(self, key):
        return None


class AppInterface(object):
    QUALITY_LOCAL = 0
    QUALITY_REMOTE = 1
    QUALITY_ONLINE = 2

    def getPreference(self, pref, default=None):
        raise NotImplementedError

    def setPreference(self, pref, value):
        raise NotImplementedError

    def clearRegistry(self, reg, sec=None):
        raise NotImplementedError

    def getRegistry(self, reg, default=None, sec=None):
        raise NotImplementedError

    def setRegistry(self, reg, value, sec=None):
        raise NotImplementedError

    def getGlobal(self, glbl, default=None):
        raise NotImplementedError

    def getCapabilities(self):
        raise NotImplementedError

    def LOG(self, msg):
        raise NotImplementedError

    def DEBUG_LOG(self, msg):
        self.LOG(msg)

    def WARN_LOG(self, msg):
        self.LOG(msg)

    def ERROR_LOG(self, msg):
        self.LOG(msg)

    def ERROR(self, msg=None, err=None):
        self.LOG(msg)

    def FATAL(self, msg=None):
        self.ERROR_LOG('FATAL: {0}'.format(msg))

    def supportsAudioStream(self, codec, channels):
        return False

    def supportsSurroundSound(self):
        return False

    def getMaxResolution(self, quality_type, allow4k=False):
        return 480

    def getQualityIndex(self, qualityType):
        if qualityType == self.QUALITY_LOCAL:
            return self.getPreference("local_quality", 0)
        elif qualityType == self.QUALITY_ONLINE:
            return self.getPreference("online_quality", 0)
        else:
            return self.getPreference("remote_quality", 0)

    def settingsGetMaxResolution(self, qualityType, allow4k):
        qualityIndex = self.getQualityIndex(qualityType)

        if qualityIndex >= 9:
            return allow4k and 2160 or 1088
        elif qualityIndex >= 6:
            return 720
        elif qualityIndex >= 5:
            return 480
        else:
            return 360

    def getMaxBitrate(self, qualityType):
        qualityIndex = self.getQualityIndex(qualityType)

        qualities = self.getGlobal("qualities", [])
        for quality in qualities:
            if quality.index == qualityIndex:
                return util.validInt(quality.maxBitrate)

        return 0


class DumbInterface(AppInterface):
    _prefs = {}
    _regs = {
        None: {}
    }
    _globals = {
        'platform': platform.uname()[0],
        'appVersionStr': '0.0.0a1',
        'clientIdentifier': str(hex(uuid.getnode())),
        'platformVersion': platform.uname()[2],
        'product': 'PlexNet.API',
        'provides': 'player',
        'device': platform.uname()[0],
        'model': 'Unknown',
        'friendlyName': 'PlexNet.API',
        'deviceInfo': DeviceInfo()
    }

    def getPreference(self, pref, default=None):
        return self._prefs.get(pref, default)

    def setPreference(self, pref, value):
        self._prefs[pref] = value

    def getRegistry(self, reg, default=None, sec=None):
        section = self._regs.get(sec)
        if section:
            return section.get(reg, default)

        return default

    def setRegistry(self, reg, value, sec=None):
        if sec and sec not in self._regs:
            self._regs[sec] = {}
        self._regs[sec][reg] = value

    def clearRegistry(self, reg, sec=None):
        del self._regs[sec][reg]

    def getGlobal(self, glbl, default=None):
        return self._globals.get(glbl, default)

    def getCapabilities(self):
        return ''

    def LOG(self, msg):
        print 'PlexNet.API: {0}'.format(msg)

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
            import traceback
            traceback.print_exc()


class CompatEvent(threading._Event):
    def wait(self, timeout):
        threading._Event.wait(self, timeout)
        return self.isSet()


class Timer(object):
    def __init__(self, timeout, function, repeat=False, *args, **kwargs):
        self.function = function
        self.timeout = timeout
        self.repeat = repeat
        self.args = args
        self.kwargs = kwargs
        self._reset = False
        self.event = CompatEvent()
        self.start()

    def start(self):
        self.event.clear()
        self.thread = threading.Thread(target=self.run, name='TIMER:{0}'.format(self.function), *self.args, **self.kwargs)
        self.thread.start()

    def run(self):
        util.DEBUG_LOG('Timer {0}: STARTED'.format(repr(self.function)))
        while not self.event.isSet() and not self.shouldAbort():
            while not self.event.wait(self.timeout) and not self.shouldAbort():
                self.function(*self.args, **self.kwargs)
                if not self.repeat:
                    break

        util.DEBUG_LOG('Timer {0}: FINISHED'.format(repr(self.function)))

    def cancel(self):
        self.event.set()

    def reset(self):
        self.cancel()
        if self.thread and self.thread.isAlive():
            self.thread.join()
        self.start()

    def shouldAbort(self):
        return False

    def join(self):
        if self.thread.isAlive():
            self.thread.join()

TIMER = Timer


def createTimer(timeout, function, repeat=False, *args, **kwargs):
    timer = TIMER(timeout / 1000.0, function, repeat=repeat, *args, **kwargs)
    return timer


def setTimer(timer):
    global TIMER
    TIMER = timer


def setInterface(interface):
    global INTERFACE
    INTERFACE = interface


def setApp(app):
    global APP
    APP = app


def refreshResources(force=False):
    import gdm
    gdm.DISCOVERY.discover()
    MANAGER.refreshResources(force)
    SERVERMANAGER.refreshManualConnections()


setApp(App())
setInterface(DumbInterface())
