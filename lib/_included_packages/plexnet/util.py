import sys
import platform
import uuid

import compat
import plexapp

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
    }

# Core Settings
PROJECT = 'PlexNet'                                 # name provided to plex server
VERSION = '0.0.0a1'                                  # version of this api
TIMEOUT = 10                                        # request timeout
X_PLEX_CONTAINER_SIZE = 50                          # max results to return in a single search page

# Plex Header Configuation
X_PLEX_PROVIDES = 'player,controller'          # one or more of [player, controller, server]
X_PLEX_PLATFORM = platform.uname()[0]          # Platform name, eg iOS, MacOSX, Android, LG, etc
X_PLEX_PLATFORM_VERSION = platform.uname()[2]  # Operating system version, eg 4.3.1, 10.6.7, 3.2
X_PLEX_PRODUCT = PROJECT                       # Plex application name, eg Laika, Plex Media Server, Media Link
X_PLEX_VERSION = VERSION                       # Plex application version number

try:
    _platform = platform.platform()
except:
    try:
        _platform = platform.platform(terse=True)
    except:
        _platform = sys.platform

X_PLEX_DEVICE = _platform                     # Device name and model number, eg iPhone3,2, Motorola XOOM, LG5200TV
X_PLEX_IDENTIFIER = str(hex(uuid.getnode()))  # UUID, serial number, or other number unique per device

BASE_HEADERS = resetBaseHeaders()


def LOG(msg):
    plexapp.INTERFACE.LOG(msg)


def DEBUG_LOG(msg):
    plexapp.INTERFACE.LOG(msg)


def ERROR_LOG(msg):
    plexapp.INTERFACE.DEBUG_LOG(msg)


def WARN_LOG(msg):
    plexapp.INTERFACE.WARN_LOG(msg)


def ERROR(msg=None, err=None):
    plexapp.INTERFACE.ERROR(msg, err)


def hideToken(token):
    # return 'X' * len(token)
    return '*' * (len(token) - 4) + token[-4:]


def joinArgs(args):
    if not args:
        return ''

    arglist = []
    for key in sorted(args, key=lambda x: x.lower()):
        value = str(args[key])
        arglist.append('{0}={1}'.format(key, compat.quote(value)))

    return '?{0}'.format('&'.join(arglist))


def addPlexHeaders(transferObj, token=None):
    transferObj.addHeader("X-Plex-Platform", plexapp.INTERFACE.getGlobal("platform"))
    transferObj.addHeader("X-Plex-Version", plexapp.INTERFACE.getGlobal("appVersionStr"))
    transferObj.addHeader("X-Plex-Client-Identifier", plexapp.INTERFACE.getGlobal("clientIdentifier"))
    transferObj.addHeader("X-Plex-Platform-Version", plexapp.INTERFACE.getGlobal("platformVersion", "unknown"))
    transferObj.addHeader("X-Plex-Product", plexapp.INTERFACE.getGlobal("product"))
    transferObj.addHeader("X-Plex-Provides", not plexapp.INTERFACE.getPreference("remotecontrol", False) and 'player' or '')
    transferObj.addHeader("X-Plex-Device", plexapp.INTERFACE.getGlobal("device"))
    transferObj.addHeader("X-Plex-Model", plexapp.INTERFACE.getGlobal("model"))
    transferObj.addHeader("X-Plex-Device-Name", plexapp.INTERFACE.getGlobal("friendlyName"))

    # Adding the X-Plex-Client-Capabilities header causes node.plexapp.com to 500
    if not type(transferObj) == "roUrlTransfer" or 'node.plexapp.com' not in transferObj.getUrl():
        transferObj.addHeader("X-Plex-Client-Capabilities", plexapp.INTERFACE.getCapabilities())

    addAccountHeaders(transferObj, token)


def addAccountHeaders(transferObj, token=None):
    if token:
        transferObj.addHeader("X-Plex-Token", token)

    # TODO(schuyler): Add username?
