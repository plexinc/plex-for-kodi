from __future__ import absolute_import
from . import simpleobjects
import re
import sys
import time
import platform
import uuid
import threading
import six

from . import verlib
from . import compat

if six.PY2:
    Event = threading._Event
else:
    Event = threading.Event

BASE_HEADERS = ''


def resetBaseHeaders():
    return {
        'X-Plex-Platform': X_PLEX_PLATFORM,
        'X-Plex-Platform-Version': X_PLEX_PLATFORM_VERSION,
        'X-Plex-Provides': X_PLEX_PROVIDES,
        'X-Plex-Product': X_PLEX_PRODUCT,
        'X-Plex-Version': X_PLEX_VERSION,
        'X-Plex-Device': X_PLEX_DEVICE,
        'X-Plex-Client-Identifier': X_PLEX_IDENTIFIER,
        'Accept-Encoding': 'gzip,deflate',
        'User-Agent': USER_AGENT
    }


# Core Settings
PROJECT = 'PlexNet'                                 # name provided to plex server
VERSION = '0.0.0a1'                                 # version of this api
TIMEOUT = 10                                        # request timeout
X_PLEX_CONTAINER_SIZE = 50                          # max results to return in a single search page

# Plex Header Configuation
X_PLEX_PROVIDES = 'player,controller'          # one or more of [player, controller, server]
X_PLEX_PLATFORM = platform.uname()[0]          # Platform name, eg iOS, MacOSX, Android, LG, etc
X_PLEX_PLATFORM_VERSION = platform.uname()[2]  # Operating system version, eg 4.3.1, 10.6.7, 3.2
X_PLEX_PRODUCT = PROJECT                       # Plex application name, eg Laika, Plex Media Server, Media Link
X_PLEX_VERSION = VERSION                       # Plex application version number
USER_AGENT = '{0}/{1}'.format(PROJECT, VERSION)

INTERFACE = None
TIMER = None
APP = None
MANAGER = None

try:
    _platform = platform.system()
except:
    try:
        _platform = platform.platform(terse=True)
    except:
        _platform = sys.platform

X_PLEX_DEVICE = _platform                     # Device name and model number, eg iPhone3,2, Motorola XOOM, LG5200TV
X_PLEX_IDENTIFIER = str(hex(uuid.getnode()))  # UUID, serial number, or other number unique per device

BASE_HEADERS = resetBaseHeaders()

QUALITY_LOCAL = 0
QUALITY_REMOTE = 1
QUALITY_ONLINE = 2

Res = simpleobjects.Res
AttributeDict = simpleobjects.AttributeDict


def setInterface(interface):
    global INTERFACE
    INTERFACE = interface


def setTimer(timer):
    global TIMER
    TIMER = timer


def setApp(app):
    global APP
    APP = app


def LOG(msg):
    INTERFACE.LOG(msg)


def DEBUG_LOG(msg):
    INTERFACE.DEBUG_LOG(msg)


def ERROR_LOG(msg):
    INTERFACE.ERROR_LOG(msg)


def WARN_LOG(msg):
    INTERFACE.WARN_LOG(msg)


def ERROR(msg=None, err=None):
    INTERFACE.ERROR(msg, err)


def FATAL(msg=None):
    INTERFACE.FATAL(msg)


def TEST(msg):
    INTERFACE.LOG(' ---TEST: {0}'.format(msg))


def userAgent():
    return INTERFACE.getGlobal("userAgent")


def dummyTranslate(string):
    return string


def hideToken(token):
    # return 'X' * len(token)
    if not token:
        return token
    return '****' + token[-4:]


def cleanToken(url):
    return re.sub('X-Plex-Token=[^&]+', 'X-Plex-Token=****', url)


def now(local=False):
    if local:
        return time.time()
    else:
        return time.mktime(time.gmtime())


def joinArgs(args):
    if not args:
        return ''

    arglist = []
    for key in sorted(args, key=lambda x: x.lower()):
        value = str(args[key])
        arglist.append('{0}={1}'.format(key, compat.quote(value)))

    return '?{0}'.format('&'.join(arglist))


def addPlexHeaders(transferObj, token=None):
    transferObj.addHeader("X-Plex-Platform", INTERFACE.getGlobal("platform"))
    transferObj.addHeader("X-Plex-Version", INTERFACE.getGlobal("appVersionStr"))
    transferObj.addHeader("X-Plex-Client-Identifier", INTERFACE.getGlobal("clientIdentifier"))
    transferObj.addHeader("X-Plex-Platform-Version", INTERFACE.getGlobal("platformVersion", "unknown"))
    transferObj.addHeader("X-Plex-Product", INTERFACE.getGlobal("product"))
    transferObj.addHeader("X-Plex-Provides", not INTERFACE.getPreference("remotecontrol", False) and 'player' or '')
    transferObj.addHeader("X-Plex-Device", INTERFACE.getGlobal("device"))
    transferObj.addHeader("X-Plex-Model", INTERFACE.getGlobal("model"))
    transferObj.addHeader("X-Plex-Device-Name", INTERFACE.getGlobal("friendlyName"))

    # Adding the X-Plex-Client-Capabilities header causes node.plexapp.com to 500
    if not type(transferObj) == "roUrlTransfer" or 'node.plexapp.com' not in transferObj.getUrl():
        transferObj.addHeader("X-Plex-Client-Capabilities", INTERFACE.getCapabilities())

    addAccountHeaders(transferObj, token)


def addAccountHeaders(transferObj, token=None):
    if token:
        transferObj.addHeader("X-Plex-Token", token)

    # TODO(schuyler): Add username?


def validInt(int_str):
    try:
        return int(int_str)
    except:
        return 0


def bitrateToString(bits):
    if not bits:
        return ''

    speed = bits / 1000000.0
    if speed < 1:
        speed = int(round(bits / 1000.0))
        return '{0} Kbps'.format(speed)
    else:
        return '{0:.1f} Mbps'.format(speed)


def normalizedVersion(ver):
    try:
        modv = '.'.join(ver.split('.')[:4]).split('-', 1)[0]  # Clean the version i.e. Turn 1.2.3.4-asdf8-ads7f into 1.2.3.4
        return verlib.NormalizedVersion(verlib.suggest_normalized_version(modv))
    except:
        if ver:
            ERROR()
        return verlib.NormalizedVersion(verlib.suggest_normalized_version('0.0.0'))


class CompatEvent(Event):
    def wait(self, timeout):
        Event.wait(self, timeout)
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
        DEBUG_LOG('Timer {0}: {1}'.format(repr(self.function), self._reset and 'RESET'or 'STARTED'))
        try:
            while not self.event.isSet() and not self.shouldAbort():
                while not self.event.wait(self.timeout) and not self.shouldAbort():
                    if self._reset:
                        return

                    self.function(*self.args, **self.kwargs)
                    if not self.repeat:
                        return
        finally:
            if not self._reset:
                if self in APP.timers:
                    APP.timers.remove(self)

                DEBUG_LOG('Timer {0}: FINISHED'.format(repr(self.function)))

            self._reset = False

    def cancel(self):
        self.event.set()

    def reset(self):
        self._reset = True
        self.cancel()
        if self.thread and self.thread.is_alive():
            self.thread.join()
        self.start()

    def shouldAbort(self):
        return False

    def join(self):
        if self.thread.is_alive():
            self.thread.join()

    def isExpired(self):
        return self.event.isSet()


TIMER = Timer
