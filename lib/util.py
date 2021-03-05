# -*- coding: utf-8 -*-
from __future__ import absolute_import
import gc
import sys
import re
import binascii
import json
import threading
import math
import time
import datetime
import contextlib
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error

from .kodijsonrpc import rpc
from kodi_six import xbmc
from kodi_six import xbmcgui
from kodi_six import xbmcaddon

from plexnet import signalsmixin
import six

DEBUG = True
_SHUTDOWN = False

ADDON = xbmcaddon.Addon()

PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))

SETTINGS_LOCK = threading.Lock()

_splitver = xbmc.getInfoLabel('System.BuildVersion').split()[0].split(".")
KODI_VERSION_MAJOR, KODI_VERSION_MINOR = int(_splitver[0].split("-")[0]), int(_splitver[1].split("-")[0])


class UtilityMonitor(xbmc.Monitor, signalsmixin.SignalsMixin):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self, *args, **kwargs)
        signalsmixin.SignalsMixin.__init__(self)

    def watchStatusChanged(self):
        self.trigger('changed.watchstatus')

    def onNotification(self, sender, method, data):
        if sender == 'script.plex' and method.endswith('RESTORE'):
            from .windows import kodigui
            getAdvancedSettings()
            populateTimeFormat()
            xbmc.executebuiltin('ActivateWindow({0})'.format(kodigui.BaseFunctions.lastWinID))


MONITOR = UtilityMonitor()


def T(ID, eng=''):
    return ADDON.getLocalizedString(ID)


def LOG(msg, level=xbmc.LOGINFO):
    xbmc.log('script.plex: {0}'.format(msg), level)


def getSetting(key, default=None):
    with SETTINGS_LOCK:
        setting = ADDON.getSetting(key)
        return _processSetting(setting, default)


def _processSetting(setting, default):
    if not setting:
        return default
    if isinstance(default, bool):
        return setting.lower() == 'true'
    elif isinstance(default, float):
        return float(setting)
    elif isinstance(default, int):
        return int(float(setting or 0))
    elif isinstance(default, list):
        if setting:
            return json.loads(binascii.unhexlify(setting))
        else:
            return default

    return setting


class AdvancedSettings(object):
    """
    @DynamicAttrs
    """

    _proxiedSettings = (
        ("debug", False),
        ("kodi_skip_stepping", False),
        ("auto_seek", True),
        ("dynamic_timeline_seek", False),
        ("fast_back", False),
        ("intro_skip_early", False)
    )

    def __init__(self):
        # register every known setting camelCased as an attribute to this instance
        for setting, default in self._proxiedSettings:
            name_split = setting.split("_")
            setattr(self, name_split[0] + ''.join(x.capitalize() or '_' for x in name_split[1:]),
                    getSetting(setting, default))


advancedSettings = AdvancedSettings()


def getAdvancedSettings():
    # yes, global, hang me!
    global advancedSettings
    advancedSettings = AdvancedSettings()


def DEBUG_LOG(msg):
    if _SHUTDOWN:
        return

    if not advancedSettings.debug and not xbmc.getCondVisibility('System.GetBool(debug.showloginfo)'):
        return

    LOG(msg)


def ERROR(txt='', hide_tb=False, notify=False):
    short = str(sys.exc_info()[1])
    if hide_tb:
        xbmc.log('script.plex: ERROR: {0} - {1}'.format(txt, short), xbmc.LOGERROR)
        return short

    import traceback
    tb = traceback.format_exc()
    xbmc.log("_________________________________________________________________________________", xbmc.LOGERROR)
    xbmc.log('script.plex: ERROR: ' + txt, xbmc.LOGERROR)
    for l in tb.splitlines():
        xbmc.log('    ' + l, xbmc.LOGERROR)
    xbmc.log("_________________________________________________________________________________", xbmc.LOGERROR)
    xbmc.log("`", xbmc.LOGERROR)
    if notify:
        showNotification('ERROR: {0}'.format(short))
    return short


def TEST(msg):
    xbmc.log('---TEST: {0}'.format(msg), xbmc.LOGINFO)


def setSetting(key, value):
    with SETTINGS_LOCK:
        value = _processSettingForWrite(value)
        ADDON.setSetting(key, value)


def _processSettingForWrite(value):
    if isinstance(value, list):
        value = binascii.hexlify(json.dumps(value))
    elif isinstance(value, bool):
        value = value and 'true' or 'false'
    return str(value)


def setGlobalProperty(key, val):
    xbmcgui.Window(10000).setProperty('script.plex.{0}'.format(key), val)


def setGlobalBoolProperty(key, boolean):
    xbmcgui.Window(10000).setProperty('script.plex.{0}'.format(key), boolean and '1' or '')


def getGlobalProperty(key):
    return xbmc.getInfoLabel('Window(10000).Property(script.plex.{0})'.format(key))


def showNotification(message, time_ms=3000, icon_path=None, header=ADDON.getAddonInfo('name')):
    try:
        icon_path = icon_path or xbmc.translatePath(ADDON.getAddonInfo('icon')).decode('utf-8')
        xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(header, message, time_ms, icon_path))
    except RuntimeError:  # Happens when disabling the addon
        LOG(message)


def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')


def messageDialog(heading='Message', msg=''):
    from .windows import optionsdialog
    optionsdialog.show(heading, msg, 'OK')


def showTextDialog(heading, text):
    t = TextBox()
    t.setControls(heading, text)


def sortTitle(title):
    return title.startswith('The ') and title[4:] or title


def durationToText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds / 86400000)
    if days:
        return '{0} day{1}'.format(days, days > 1 and 's' or '')
    left = seconds % 86400000
    hours = int(left / 3600000)
    if hours:
        hours = '{0} hr{1} '.format(hours, hours > 1 and 's' or '')
    else:
        hours = ''
    left = left % 3600000
    mins = int(left / 60000)
    if mins:
        return hours + '{0} min{1}'.format(mins, mins > 1 and 's' or '')
    elif hours:
        return hours.rstrip()
    secs = int(left % 60000)
    if secs:
        secs /= 1000
        return '{0} sec{1}'.format(secs, secs > 1 and 's' or '')
    return '0 seconds'


def durationToShortText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds / 86400000)
    if days:
        return '{0} d'.format(days)
    left = seconds % 86400000
    hours = int(left / 3600000)
    if hours:
        hours = '{0} h '.format(hours)
    else:
        hours = ''
    left = left % 3600000
    mins = int(left / 60000)
    if mins:
        return hours + '{0} m'.format(mins)
    elif hours:
        return hours.rstrip()
    secs = int(left % 60000)
    if secs:
        secs /= 1000
        return '{0} s'.format(secs)
    return '0 s'


def cleanLeadingZeros(text):
    if not text:
        return ''
    return re.sub('(?<= )0(\d)', r'\1', text)


def removeDups(dlist):
    return [ii for n, ii in enumerate(dlist) if ii not in dlist[:n]]


SIZE_NAMES = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


def simpleSize(size):
    """
    Converts bytes to a short user friendly string
    Example: 12345 -> 12.06 KB
    """
    s = 0
    if size > 0:
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)
    if (s > 0):
        return '%s %s' % (s, SIZE_NAMES[i])
    else:
        return '0B'


def timeDisplay(ms):
    h = ms / 3600000
    m = (ms % 3600000) / 60000
    s = (ms % 60000) / 1000
    return '{0:0>2}:{1:0>2}:{2:0>2}'.format(int(h), int(m), int(s))


def simplifiedTimeDisplay(ms):
    left, right = timeDisplay(ms).rsplit(':', 1)
    left = left.lstrip('0:') or '0'
    return left + ':' + right


def shortenText(text, size):
    if len(text) < size:
        return text

    return u'{0}\u2026'.format(text[:size - 1])


class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % (self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)

    def setControls(self, heading, text):
        # set heading
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)


class SettingControl:
    def __init__(self, setting, log_display, disable_value=''):
        self.setting = setting
        self.logDisplay = log_display
        self.disableValue = disable_value
        self._originalMode = None
        self.store()

    def disable(self):
        rpc.Settings.SetSettingValue(setting=self.setting, value=self.disableValue)
        DEBUG_LOG('{0}: DISABLED'.format(self.logDisplay))

    def set(self, value):
        rpc.Settings.SetSettingValue(setting=self.setting, value=value)
        DEBUG_LOG('{0}: SET={1}'.format(self.logDisplay, value))

    def store(self):
        try:
            self._originalMode = rpc.Settings.GetSettingValue(setting=self.setting).get('value')
            DEBUG_LOG('{0}: Mode stored ({1})'.format(self.logDisplay, self._originalMode))
        except:
            ERROR()

    def restore(self):
        if self._originalMode is None:
            return
        rpc.Settings.SetSettingValue(setting=self.setting, value=self._originalMode)
        DEBUG_LOG('{0}: RESTORED'.format(self.logDisplay))

    @contextlib.contextmanager
    def suspend(self):
        self.disable()
        yield
        self.restore()

    @contextlib.contextmanager
    def save(self):
        yield
        self.restore()


def timeInDayLocalSeconds():
    now = datetime.datetime.now()
    sod = datetime.datetime(year=now.year, month=now.month, day=now.day)
    sod = int(time.mktime(sod.timetuple()))
    return int(time.time() - sod)


def getKodiSkipSteps():
    try:
        return rpc.Settings.GetSettingValue(setting="videoplayer.seeksteps")["value"]
    except:
        return


kodiSkipSteps = getKodiSkipSteps()


CRON = None


class CronReceiver():
    def tick(self):
        pass

    def halfHour(self):
        pass

    def day(self):
        pass


class Cron(threading.Thread):
    def __init__(self, interval):
        threading.Thread.__init__(self, name='CRON')
        self.stopped = threading.Event()
        self.force = threading.Event()
        self.interval = interval
        self._lastHalfHour = self._getHalfHour()
        self._receivers = []

        global CRON

        CRON = self

    def __enter__(self):
        self.start()
        DEBUG_LOG('Cron started')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        self.join()

    def _wait(self):
        ct = 0
        while ct < self.interval:
            xbmc.sleep(100)
            ct += 0.1
            if self.force.isSet():
                self.force.clear()
                return True
            if MONITOR.abortRequested() or self.stopped.isSet():
                return False
        return True

    def forceTick(self):
        self.force.set()

    def stop(self):
        self.stopped.set()

    def run(self):
        while self._wait():
            self._tick()
        DEBUG_LOG('Cron stopped')

    def _getHalfHour(self):
        tid = timeInDayLocalSeconds() / 60
        return tid - (tid % 30)

    def _tick(self):
        receivers = list(self._receivers)
        receivers = self._halfHour(receivers)
        for r in receivers:
            try:
                r.tick()
            except:
                ERROR()

    def _halfHour(self, receivers):
        hh = self._getHalfHour()
        if hh == self._lastHalfHour:
            return receivers
        try:
            receivers = self._day(receivers, hh)
            ret = []
            for r in receivers:
                try:
                    if not r.halfHour():
                        ret.append(r)
                except:
                    ret.append(r)
                    ERROR()
            return ret
        finally:
            self._lastHalfHour = hh

    def _day(self, receivers, hh):
        if hh >= self._lastHalfHour:
            return receivers
        ret = []
        for r in receivers:
            try:
                if not r.day():
                    ret.append(r)
            except:
                ret.append(r)
                ERROR()
        return ret

    def registerReceiver(self, receiver):
        if receiver not in self._receivers:
            DEBUG_LOG('Cron: Receiver added: {0}'.format(receiver))
            self._receivers.append(receiver)

    def cancelReceiver(self, receiver):
        if receiver in self._receivers:
            DEBUG_LOG('Cron: Receiver canceled: {0}'.format(receiver))
            self._receivers.pop(self._receivers.index(receiver))



def getTimeFormat():
    """
    Get global time format.
    Kodi's time format handling is broken right now, as they return incompatible formats for strftime.
    %H%H is being returned for manually set zero-padded values, in case of a regional zero-padded hour component,
    only %H is returned.

    For now, sail around that by testing the current time for padded hour values.

    Tests of the values returned by xbmc.getRegion("time"):
    %I:%M:%S %p = h:mm:ss, non-zero-padded, 12h PM
    %I:%M:%S = 12h, h:mm:ss, non-zero-padded, regional
    %I%I:%M:%S = 12h, zero padded, hh:mm:ss
    %H%H:%M:%S = 24h, zero padded, hh:mm:ss
    %H:%M:%S = 24h, zero padded, regional, regional (central europe)

    :return: tuple of strftime-compatible format, boolean padHour
    """
    origFmt = xbmc.getRegion('time')
    fmt = origFmt.replace("%H%H", "%H").replace("%I%I", "%I")

    # Checking for %H%H or %I%I only would be the obvious way here to determine whether the hour should be padded,
    # but the formats returned for regional settings with padding only have %H in them. This seems like a Kodi bug.
    # Use a fallback.
    currentTime = xbmc.getInfoLabel('System.Time')
    padHour = "%H%H" in origFmt or "%I%I" in origFmt or (currentTime[0] == "0" and currentTime[1] != ":")
    return fmt, padHour


timeFormat, padHour = getTimeFormat()


def populateTimeFormat():
    global timeFormat, padHour
    timeFormat, padHour = getTimeFormat()


def getPlatform():
    for key in [
        'System.Platform.Android',
        'System.Platform.Linux.RaspberryPi',
        'System.Platform.Linux',
        'System.Platform.Windows',
        'System.Platform.OSX',
        'System.Platform.IOS',
        'System.Platform.Darwin',
        'System.Platform.ATV2'
    ]:
        if xbmc.getCondVisibility(key):
            return key.rsplit('.', 1)[-1]


def getProgressImage(obj):
    if not obj.get('viewOffset'):
        return ''
    pct = int((obj.viewOffset.asInt() / obj.duration.asFloat()) * 100)
    pct = pct - pct % 2  # Round to even number - we have even numbered progress only
    pct = max(pct, 2)
    return 'script.plex/progress/{0}.png'.format(pct)


def trackIsPlaying(track):
    return xbmc.getCondVisibility('String.StartsWith(MusicPlayer.Comment,{0})'.format('PLEX-{0}:'.format(track.ratingKey)))


def addURLParams(url, params):
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += six.moves.urllib.parse.urlencode(params)
        return url


def garbageCollect():
    gc.collect(2)


def shutdown():
    global MONITOR, ADDON, T, _SHUTDOWN
    _SHUTDOWN = True
    del MONITOR
    del T
    del ADDON


def getAttributes():
    # TODO replace source
    return {
        "title": "Kodi",
        "machineIdentifier": "plex-kodi-plex-xxxxxx",
        "product": "Plex for Kodi",
        "version": "0.0.1",
        "platform": "RaspberryPi",
        "platformVersion": "18.0.0",
        "protocolVersion": "3",
        "protocolCapabilities": "timeline,playback,navigation,mirror,playqueues",
        "deviceClass": "stb"
    }
