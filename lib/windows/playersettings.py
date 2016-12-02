import xbmc
import kodigui

from lib import util
from lib import metadata
from lib.util import T

import plexnet


class VideoSettingsDialog(kodigui.BaseDialog, util.CronReceiver):
    xmlFile = 'script-plex-video_settings_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SETTINGS_LIST_ID = 100

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.viaOSD = kwargs.get('via_osd')
        self.nonPlayback = kwargs.get('non_playback')

        if not self.video.mediaChoice:
            playerObject = plexnet.plexplayer.PlexPlayer(self.video)
            playerObject.build()

    def onFirstInit(self):
        self.settingsList = kodigui.ManagedControlList(self, self.SETTINGS_LIST_ID, 6)
        self.setProperty('heading', T(32343, 'Settings'))
        if self.viaOSD:
            self.setProperty('via.OSD', '1')
        self.showSettings(True)
        util.CRON.registerReceiver(self)

    def onAction(self, action):
        try:
            if not xbmc.getCondVisibility('Player.HasMedia') and not self.nonPlayback:
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SETTINGS_LIST_ID:
            self.editSetting()

    def onClosed(self):
        util.CRON.cancelReceiver(self)

    def tick(self):
        if self.nonPlayback:
            return

        if not xbmc.getCondVisibility('Player.HasMedia'):
            self.doClose()
            return

    def showSettings(self, init=False):
        video = self.video
        override = video.settings.getPrefOverride('local_quality')
        if override is not None and override < 13:
            current = T((32001, 32002, 32003, 32004, 32005, 32006, 32007, 32008, 32009, 32010, 32011, 32012, 32013, 32014)[13 - override])
        else:
            current = u'{0} {1} ({2})'.format(
                plexnet.util.bitrateToString(video.mediaChoice.media.bitrate.asInt() * 1000),
                video.mediaChoice.media.getVideoResolutionString(),
                video.mediaChoice.media.title or 'Original'
            )

        audio, subtitle = self.getAudioAndSubtitleInfo()

        options = [
            ('audio', T(32395, 'Audio'), audio),
            ('subs', T(32396, 'Subtitles'), subtitle),
            ('quality', T(32397, 'Quality'), u'{0}'.format(current))
        ]

        if not self.nonPlayback:
            options += [
                ('kodi_video', T(32398, 'Kodi Video Settings'), ''),
                ('kodi_audio', T(32399, 'Kodi Audio Settings'), '')
            ]

        items = []
        for o in options:
            item = kodigui.ManagedListItem(o[1], o[2], data_source=o[0])
            items.append(item)
        if init:
            self.settingsList.reset()
            self.settingsList.addItems(items)
        else:
            self.settingsList.replaceItems(items)

        self.setFocusId(self.SETTINGS_LIST_ID)

    def getAudioAndSubtitleInfo(self):
        sas = self.video.selectedAudioStream()
        audio = sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None')

        sss = self.video.selectedSubtitleStream()
        if sss:
            if len(self.video.subtitleStreams) > 1:
                subtitle = u'{0} \u2022 {1} {2}'.format(sss.getTitle(metadata.apiTranslate), len(self.video.subtitleStreams) - 1, T(32307, 'More'))
            else:
                subtitle = sss.getTitle(metadata.apiTranslate)
        else:
            if self.video.subtitleStreams:
                subtitle = u'{0} \u2022 {1} {2}'.format(T(32309, 'None'), len(self.video.subtitleStreams), T(32308, 'Available'))
            else:
                subtitle = T(32309, 'None')

        return audio, subtitle

    def editSetting(self):
        mli = self.settingsList.getSelectedItem()
        if not mli:
            return

        result = mli.dataSource

        if result == 'audio':
            showAudioDialog(self.video, non_playback=self.nonPlayback)
        elif result == 'subs':
            showSubtitlesDialog(self.video, non_playback=self.nonPlayback)
        elif result == 'quality':
            idx = None
            override = self.video.settings.getPrefOverride('local_quality')
            if override is not None and override < 13:
                idx = 13 - override
            showQualityDialog(self.video, non_playback=self.nonPlayback, selected_idx=idx)
        elif result == 'kodi_video':
            xbmc.executebuiltin('ActivateWindow(OSDVideoSettings)')
        elif result == 'kodi_audio':
            xbmc.executebuiltin('ActivateWindow(OSDAudioSettings)')

        self.showSettings()


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
        self.selectedIdx = kwargs.get('selected_idx')
        self.choice = None
        self.nonPlayback = kwargs.get('non_playback')

    def onFirstInit(self):
        self.optionsList = kodigui.ManagedControlList(self, self.OPTIONS_LIST_ID, 8)
        self.setProperty('heading', self.heading)
        self.showOptions()
        util.CRON.registerReceiver(self)

    def onAction(self, action):
        try:
            if not xbmc.getCondVisibility('Player.HasMedia') and not self.nonPlayback:
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
        if self.nonPlayback:
            return

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

        if self.selectedIdx is not None:
            self.optionsList.selectItem(self.selectedIdx)

        self.setFocusId(self.OPTIONS_LIST_ID)


def showOptionsDialog(heading, options, non_playback=False, selected_idx=None):
    w = SelectDialog.open(heading=heading, options=options, non_playback=non_playback, selected_idx=selected_idx)
    choice = w.choice
    del w
    util.garbageCollect()
    return choice


def showAudioDialog(video, non_playback=False):
    options = []
    idx = None
    for i, s in enumerate(video.audioStreams):
        if s.isSelected():
            idx = i
        options.append((s, s.getTitle(metadata.apiTranslate)))
    choice = showOptionsDialog(T(32395, 'Audio'), options, non_playback=non_playback, selected_idx=idx)
    if choice is None:
        return

    video.selectStream(choice)


def showSubtitlesDialog(video, non_playback=False):
    options = [(plexnet.plexstream.NoneStream(), 'None')]
    idx = None
    for i, s in enumerate(video.subtitleStreams):
        if s.isSelected():
            idx = i + 1
        options.append((s, s.getTitle(metadata.apiTranslate)))

    choice = showOptionsDialog(T(32396, 'Subtitle'), options, non_playback=non_playback, selected_idx=idx)
    if choice is None:
        return

    video.selectStream(choice)


def showQualityDialog(video, non_playback=False, selected_idx=None):
    options = [(13 - i, T(l)) for (i, l) in enumerate((32001, 32002, 32003, 32004, 32005, 32006, 32007, 32008, 32009, 32010, 32011, 32012, 32013, 32014))]

    choice = showOptionsDialog('Quality', options, non_playback=non_playback, selected_idx=selected_idx)
    if choice is None:
        return

    video.settings.setPrefOverride('local_quality', choice)
    video.settings.setPrefOverride('remote_quality', choice)
    video.settings.setPrefOverride('online_quality', choice)


def showDialog(video, non_playback=False, via_osd=False):
    w = VideoSettingsDialog.open(video=video, non_playback=non_playback, via_osd=via_osd)
    del w
    util.garbageCollect()
