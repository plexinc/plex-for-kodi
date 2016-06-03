import threading
import platform
import uuid

import signalsmixin
import util

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


class AppInterface(object):
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

    def ERROR(self, msg=None, err=None):
        self.LOG(msg)


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
        'device': _platform,
        'model': 'Unknown',
        'friendlyName': 'PlexNet.API',
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

    def ERROR(self, msg=None, err=None):
        if err:
            self.LOG('ERROR: {0} - {1}'.format(msg, err.message))
        else:
            import traceback
            traceback.print_exc()


class Timer(object):
    def __init__(self, timeout, function, repeat=False, *args, **kwargs):
        self.function = function
        self.timeout = timeout
        self.repeat = repeat
        self.args = args
        self.kwargs = kwargs
        self._reset = False
        self.event = threading.Event()
        self.start()

    def start(self):
        self.event.clear()
        self.thread = threading.Thread(target=self.run, *self.args, **self.kwargs)
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
