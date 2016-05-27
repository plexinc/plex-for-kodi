import threading

import callback
import eventsmixin
import util

APP = None
INTERFACE = None


class App(object):
    def __init__(self):
        self.pendingRequests = {}
        self.timers = []

    def addTimer(self, timer):
        self.timers.append(timer)

    def startRequest(request, context, body=None, contentType=None):
        context.request = request

        started = request.startAsync(body, contentType)

        if started:
            id = request.getIdentity()
            self.pendingRequests[id] = context

            if context.timeout:
                timer = createTimer(context.timeout, callback.Callable(self.OnRequestTimeout, self, [context]))
                self.addTimer(timer)
        elif context.callback:
            context.callback([None, context])

        return started

    def onRequestTimeout(context):
        requestContext = context
        request = requestContext.request
        requestID = request.GetIdentity()

        request.cancel()
        del self.pendingRequests[requestID]

        util.WARN_LOG("Request to {0} timed out after {1} seconds".format(request.url, requestContext.timeout))

        if requestContext.callback:
            requestContext.callback([None, requestContext])

    def shutdown(self):
        if self.timers:
            util.DEBUG_LOG('Shutting down App() timers: Started')
            for timer in self.timers:
                timer.cancel()

            for timer in self.timers:
                if timer.isAlive():
                    timer.join()
            util.DEBUG_LOG('Shutting down App() timers: Finished')


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

    def LOG(self, msg):
        raise NotImplementedError

    def DEBUG_LOG(self, msg):
        self.LOG(msg)

    def WARN_LOG(self, msg):
        self.LOG(msg)

    def ERROR(msg=None, err=None):
        self.LOG(msg)


class DumbInterface(AppInterface):
    _prefs = {}
    _regs = {
        None: {}
    }

    def getPreference(self, pref, default=None):
        return self._prefs.get(pref, default)

    def setPreference(self, pref, value):
        self._prefs[pref] = value

    def getRegistry(self, reg, default=None, sec=None):
        return self._regs.get[sec].get(ref, default)

    def setRegistry(self, reg, value, sec=None):
        self._regs[sec][reg] = value

    def clearRegistry(self, reg, sec=None):
        del self._regs[sec][reg]

    def addInitializer(self, sec):
        self._regs[sec] = {}

    def clearInitializer(self, sec):
        if sec in self._regs:
            del self._regs[sec]

    def getGlobal(self, glbl, default=None):
        return default

    def LOG(self, msg):
        'plexnet.api: {0}'.format(msg)

    def ERROR(msg=None, err=None):
        if err:
            LOG('ERROR: {0} - {1}'.format(msg, err.message))
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

    def run():
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
