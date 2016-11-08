import xbmc
import xbmcgui
import kodigui
import windowutils

from lib.util import T
from lib import util

import plexnet

'''
    <setting id="transcode_format" label="32023" type="labelenum" values="mkv|hls" default="0" />
    <setting id="playback_directplay_force" type="bool" label="32027" default="false" enable="eq(-1,true)" subsetting="true" />
    <setting id="burn_subtitles" label="32031" type="enum" lvalues="32028|32029|32030" default="0" />
    <setting id="allow_insecure" label="32032" type="enum" lvalues="32033|32034|32035" default = "0" />
'''


class Setting(object):
    type = None
    ID = None
    label = None
    default = None

    def translate(self, val):
        return str(val)

    def get(self):
        return util.getSetting(self.ID, self.default)

    def set(self, val):
        old = self.get()
        if old != val:
            util.DEBUG_LOG('Setting: {0} - changed from [{1}] to [{2}]'.format(self.ID, old, val))
            plexnet.plexapp.APP.trigger('change:{0}'.format(self.ID))
        return util.setSetting(self.ID, val)

    def valueLabel(self):
        return self.translate(self.get())

    def __repr__(self):
        return '<Setting {0}={1}>'.format(self.ID, self.get())


class BasicSetting(Setting):
    def __init__(self, ID, label, default):
        self.ID = ID
        self.label = label
        self.default = default


class QualitySetting(BasicSetting):
    type = 'LIST'

    QUALITY = (
        T(32001),
        T(32002),
        T(32003),
        T(32004),
        T(32005),
        T(32006),
        T(32007),
        T(32008),
        T(32009),
        T(32010),
        T(32011),
        T(32012),
        T(32013),
        T(32014),
    )

    def translate(self, val):
        return self.QUALITY[13 - val]

    def optionLabels(self):
        return self.QUALITY

    def optionIndex(self):
        return 13 - self.get()

    def set(self, val):
        BasicSetting.set(self, 13 - val)


class BoolSetting(BasicSetting):
    type = 'BOOL'


class OptionsSetting(BasicSetting):
    type = 'OPTIONS'

    def __init__(self, ID, label, default, options):
        BasicSetting.__init__(self, ID, label, default)
        self.options = options

    def translate(self, val):
        for ID, label in self.options:
            if ID == val:
                return label

    def optionLabels(self):
        return [o[1] for o in self.options]

    def optionIndex(self):
        val = self.get()
        for i, o in enumerate(self.options):
            if val == o[0]:
                return i

        return 0


class InfoSetting(BasicSetting):
    type = 'INFO'

    def __init__(self, ID, label, info):
        BasicSetting.__init__(self, ID, label, None)
        self.info = info

    def valueLabel(self):
        return self.info


class PlatformSetting(InfoSetting):
    def __init__(self):
        self.ID = 'platfom_version'
        self.label = 'Platform Version'

    def valueLabel(self):
        try:
            import platform
            dist = platform. dist()
            if dist and len(dist) > 1:
                plat = u'{0} {1}'.format(dist[0], dist[1])
            else:
                plat = platform.platform()
                plat = u'{0} {1}'.format(plat[0], '.'.join(plat[1].split('.', 2)[:2]))
        except:
            util.ERROR()

        plat = plat.strip()

        if not plat:
            if xbmc.getCondVisibility('System.Platform.Android'):
                plat = 'Android'
            elif xbmc.getCondVisibility('System.Platform.OSX'):
                plat = 'OSX'
            elif xbmc.getCondVisibility('System.Platform.Darwin'):
                plat = 'Darwin'
            elif xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
                plat = 'Linux (RPi)'
            elif xbmc.getCondVisibility('System.Platform.Linux'):
                plat = 'Linux'
            elif xbmc.getCondVisibility('System.Platform.Windows'):
                plat = 'Windows'

        return plat or 'Unknown'


class IPSetting(BasicSetting):
    type = 'IP'


class IntegerSetting(BasicSetting):
    type = 'INTEGER'


class Settings(object):
    SETTINGS = {
        'main': (
            'Main', (
                BoolSetting('auto_signin', 'Automatically Sign In', False),
                BoolSetting('post_play_auto', 'Post Play Auto Play', True),
            )
        ),
        'audio': (
            'Audio',
            ()
        ),
        'video': (
            'Video', (
                QualitySetting('local_quality', 'Local Quality', 13),
                QualitySetting('remote_quality', 'Remote Quality', 8),
                QualitySetting('online_quality', 'Online Quality', 13),
                BoolSetting('playback_directplay', 'Allow Direct Play', True),
                BoolSetting('playback_remux', 'Allow Direct Stream', True),
                BoolSetting('allow_4k', 'Allow 4K', True),
                BoolSetting('allow_hevc', 'Allow HEVC (h265)', False)
            )
        ),
        'subtitles': (
            'Subtitles', (
                OptionsSetting('burn_subtitles', 'Burn Subtitles', 'auto', (('auto', 'Auto'), ('image', 'Only Image Formats'), ('always', 'Always'))),
            )
        ),
        'advanced': (
            'Advanced', (
                OptionsSetting(
                    'allow_insecure', T(32032), 'never', (('never', T(32033)), ('same_network', T(32034)), ('always', T(32035)))
                ),
                BoolSetting('gdm_discovery', 'Server Discovery (GDM)', True),
                BoolSetting('kiosk.mode', 'Start Plex On Kodi Startup', False),
            )
        ),
        'manual': (
            'Manual Servers', (
                IPSetting('manual_ip_0', 'Connection 1 IP', ''),
                IntegerSetting('manual_port_0', 'Connection 1 Port', 32400),
                IPSetting('manual_ip_1', 'Connection 2 IP', ''),
                IntegerSetting('manual_port_1', 'Connection 2 Port', 32400)
            )
        ),
        'privacy': (
            'Privacy',
            ()
        ),
        'about': (
            'About', (
                InfoSetting('addon_version', 'Addon Version', util.ADDON.getAddonInfo('version')),
                InfoSetting('kodi_version', 'Kodi Version', xbmc.getInfoLabel('System.BuildVersion')),
                PlatformSetting(),
                InfoSetting('screen_res', 'Screen Resolution', xbmc.getInfoLabel('System.ScreenResolution').split('-')[0].strip())
            )
        ),
    }

    SECTION_IDS = ('main', 'video', 'subtitles', 'advanced', 'manual', 'about')

    def __getitem__(self, key):
        return self.SETTINGS[key]


class SettingsWindow(kodigui.BaseWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-settings.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SECTION_LIST_ID = 75
    SETTINGS_LIST_ID = 100
    OPTIONS_LIST_ID = 125
    TOP_GROUP_ID = 200

    CLOSE_BUTTON_ID = 201
    PLAYER_STATUS_BUTTON_ID = 204

    def onFirstInit(self):
        self.settings = Settings()
        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 6)
        self.settingsList = kodigui.ManagedControlList(self, self.SETTINGS_LIST_ID, 6)
        self.optionsList = kodigui.ManagedControlList(self, self.OPTIONS_LIST_ID, 6)

        self.setProperty('heading', 'Settings')
        self.showSections()
        self.setFocusId(75)
        self.lastSection = None
        self.checkSection()

    def onAction(self, action):
        try:
            self.checkSection()
            controlID = self.getFocusId()
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                if self.getFocusId() == self.OPTIONS_LIST_ID:
                    self.setFocusId(self.SETTINGS_LIST_ID)
                    return
                elif not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.TOP_GROUP_ID)):
                    self.setFocusId(self.TOP_GROUP_ID)
                    return
            elif action == xbmcgui.ACTION_MOVE_RIGHT and controlID == 150:
                self.editSetting(from_right=True)
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.setFocusId(self.SETTINGS_LIST_ID)
        elif controlID == self.SETTINGS_LIST_ID:
            self.editSetting()
        elif controlID == self.OPTIONS_LIST_ID:
            self.changeSetting()
        elif controlID == self.CLOSE_BUTTON_ID:
            self.doClose()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()

    def checkSection(self):
        mli = self.sectionList.getSelectedItem()
        if not mli:
            return

        if mli.dataSource == self.lastSection:
            return

        self.lastSection = mli.dataSource
        self.showSettings(self.lastSection)
        self.setProperty('section.about', self.lastSection == 'about' and '1' or '')
        util.DEBUG_LOG('Settings: Changed section ({0})'.format(self.lastSection))

    def showSections(self):
        items = []
        for sectionID in self.settings.SECTION_IDS:
            label = self.settings[sectionID][0]
            item = kodigui.ManagedListItem(label, data_source=sectionID)
            items.append(item)

        self.sectionList.addItems(items)

    def showSettings(self, section):
        settings = self.settings[section][1]
        if not settings:
            return self.settingsList.reset()

        items = []
        for setting in settings:
            item = kodigui.ManagedListItem(setting.label, setting.type != 'BOOL' and setting.valueLabel() or '', data_source=setting)
            if setting.type == 'BOOL':
                item.setProperty('checkbox', '1')
                item.setProperty('checkbox.checked', setting.get() and '1' or '')

            items.append(item)

        self.settingsList.reset()
        self.settingsList.addItems(items)

    def editSetting(self, from_right=False):
        mli = self.settingsList.getSelectedItem()
        if not mli:
            return

        setting = mli.dataSource

        if setting.type in ('LIST', 'OPTIONS'):
            self.fillList(setting)
        elif setting.type == 'BOOL' and not from_right:
            self.toggleBool(mli, setting)
        elif setting.type == 'IP' and not from_right:
            self.editIP(mli, setting)
        elif setting.type == 'INTEGER' and not from_right:
            self.editInteger(mli, setting)

    def changeSetting(self):
        optionItem = self.optionsList.getSelectedItem()
        if not optionItem:
            return

        mli = self.settingsList.getSelectedItem()
        if not mli:
            return

        setting = mli.dataSource

        if setting.type == 'LIST':
            setting.set(optionItem.pos())
            mli.setLabel2(setting.valueLabel())
        elif setting.type == 'OPTIONS':
            setting.set(optionItem.dataSource)
            mli.setLabel2(setting.valueLabel())

        self.setFocusId(self.SETTINGS_LIST_ID)

    def fillList(self, setting):
        items = []
        if setting.type == 'LIST':
            for label in setting.optionLabels():
                items.append(kodigui.ManagedListItem(label))
        elif setting.type == 'OPTIONS':
            for ID, label in setting.options:
                items.append(kodigui.ManagedListItem(label, data_source=ID))

        self.optionsList.reset()
        self.optionsList.addItems(items)
        self.optionsList.selectItem(setting.optionIndex())
        self.setFocusId(self.OPTIONS_LIST_ID)

    def toggleBool(self, mli, setting):
        setting.set(not setting.get())
        mli.setProperty('checkbox.checked', setting.get() and '1' or '')

    def editIP(self, mli, setting):
        current = setting.get()
        edit = True
        if current:
            edit = xbmcgui.Dialog().yesno('Edit Or Clear', 'Edit IP address or clear the current setting?', nolabel='Clear', yeslabel='Edit')

        if edit:
            result = xbmcgui.Dialog().input('Enter IP Address', current, xbmcgui.INPUT_IPADDRESS)
            if not result:
                return
        else:
            result = ''

        setting.set(result)
        mli.setLabel2(result)

    def editInteger(self, mli, setting):
        result = xbmcgui.Dialog().input('Enter Port Number', str(setting.get()), xbmcgui.INPUT_NUMERIC)
        if not result:
            return
        setting.set(int(result))
        mli.setLabel2(result)


class SelectDialog(kodigui.BaseDialog, util.CronReceiver):
    xmlFile = 'script-plex-settings_select_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_LIST_ID = 100

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.heading = kwargs.get('heading')
        self.options = kwargs.get('options')
        self.choice = None

    def onFirstInit(self):
        self.optionsList = kodigui.ManagedControlList(self, self.OPTIONS_LIST_ID, 8)
        self.setProperty('heading', self.heading)
        self.showOptions()
        util.CRON.registerReceiver(self)

    def onAction(self, action):
        try:
            if not xbmc.getCondVisibility('Player.HasMedia'):
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.OPTIONS_LIST_ID:
            self.setChoice()

    def onClosed(self):
        util.CRON.cancelReceiver(self)

    def tick(self):
        if not xbmc.getCondVisibility('Player.HasMedia'):
            self.doClose()
            return

    def setChoice(self):
        mli = self.optionsList.getSelectedItem()
        if not mli:
            return

        self.choice = self.options[self.optionsList.getSelectedPosition()][0]
        self.doClose()

    def showOptions(self):
        items = []
        for o in self.options:
            item = kodigui.ManagedListItem(o[1], data_source=o[0])
            items.append(item)

        self.optionsList.reset()
        self.optionsList.addItems(items)

        self.setFocusId(self.OPTIONS_LIST_ID)


def showOptionsDialog(heading, options):
    w = SelectDialog.open(heading=heading, options=options)
    choice = w.choice
    del w
    return choice


def showAudioDialog(video):
    options = [(s, s.getTitle()) for s in video.audioStreams]
    choice = showOptionsDialog('Audio', options)
    if choice is None:
        return

    video.selectStream(choice)


def showSubtitlesDialog(video):
    options = [(s, s.getTitle()) for s in video.subtitleStreams]
    options.insert(0, (plexnet.plexstream.NoneStream(), 'None'))
    choice = showOptionsDialog('Subtitle', options)
    if choice is None:
        return

    video.selectStream(choice)


def showQualityDialog(video):
    options = [(13 - i, T(l)) for (i, l) in enumerate((32001, 32002, 32003, 32004, 32005, 32006, 32007, 32008, 32009, 32010, 32011, 32012, 32013, 32014))]

    choice = showOptionsDialog('Quality', options)
    if choice is None:
        return

    video.settings.setPrefOverride('local_quality', choice)
    video.settings.setPrefOverride('remote_quality', choice)
    video.settings.setPrefOverride('online_quality', choice)


def openWindow():
    w = SettingsWindow.open()
    del w
