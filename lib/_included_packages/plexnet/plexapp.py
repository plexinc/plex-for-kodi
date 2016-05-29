import threading
import platform
import uuid

import eventsmixin
import util

APP = None
INTERFACE = None


class App(eventsmixin.EventsMixin):
    def __init__(self):
        eventsmixin.EventsMixin.__init__(self)
        self.pendingRequests = {}
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
            #     timer = createTimer(context.timeout, callback.Callable(self.onRequestTimeout, self, [context]))
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

    def shutdown(self):
        if self.timers:
            util.DEBUG_LOG('Shutting down App() timers: Started')
            for timer in self.timers:
                timer.cancel()

            for timer in self.timers:
                if timer.isAlive():
                    timer.join()
            util.DEBUG_LOG('Shutting down App() timers: Finished')


try:
    _platform = platform.platform()
except:
    try:
        _platform = platform.platform(terse=True)
    except:
        _platform = sys.platform


class AppInterface(eventsmixin.EventsMixin):
    def getPreference(self, pref, default=None):
        raise NotImplementedError

    def setPreference(self, pref, value):
        raise NotImplementedError

    def clearRegistry(self, reg, sec=None):
        raise NotImplementedError

    def addInitializer(self, sec):
        raise NotImplementedError

    def clearInitializer(self, sec):
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
        None: {},
        'myplex': {
            'MyPlexAccount': '{"authToken": "YMcrCsBmwj89pqxLqy66"}'
        }
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

    def addInitializer(self, sec):
        # if sec not in self._regs:
        #     self._regs[sec] = {}
        pass

    def clearInitializer(self, sec):
        # if sec in self._regs:
        #     del self._regs[sec]
        pass

    def getGlobal(self, glbl, default=None):
        return self._globals.get(glbl, default)

    def getCapabilities(self):
        return ''

    def LOG(self, msg):
        print 'PlexNet.API: {0}'.format(msg)

    def ERROR(self, msg=None, err=None):
        if err:
            self.LOG('ERROR: {0} - {1}'.format(msg, err.message))
        else:
            import traceback
            traceback.print_exc()


class RepeatableTimer(threading.Thread):
    def __init__(self, timeout, function, repeat=False, *args, **kwargs):
        self.function = function
        self.timeout = timeout
        self.repeat = repeat
        self.args = args
        self.kwargs = kwargs
        threading.Thread.__init__(self, *args, **kwargs)
        self._reset = False
        self.event = threading.Event()
        self.start()

    def run(self):
        while not self.event.isSet():
            while not self.event.wait(self.timeout):
                self.function(*self.args, **self.kwargs)
                if not self.repeat:
                    break

            if not self._reset:
                break

            self._reset = False
            self.event.clear()

    def cancel(self):
        self.event.set()

    def reset(self):
        self._reset = True
        self.cancel()


def createTimer(timeout, function, repeat=False, *args, **kwargs):
    timer = RepeatableTimer(timeout / 1000.0, function, repeat=repeat, *args, **kwargs)
    return timer


def setInterface(interface):
    global INTERFACE
    INTERFACE = interface


def setApp(app):
    global APP
    APP = app

setApp(App())
setInterface(DumbInterface())
