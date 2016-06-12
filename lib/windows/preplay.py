import kodigui
from lib import colors
from lib import util
from lib import player


class PrePlayWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-pre_play.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_POSTER_DIM = (347, 518)

    EXTRA_LIST_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201

    PLAY_BUTTON_ID = 301

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.exitCommand = None

    def onFirstInit(self):
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)

        self.setInfo()
        self.fillExtras()
        self.setFocusId(self.PLAY_BUTTON_ID)

    # def onAction(self, action):
    #     try:
    #         if action == xbmcgui.ACTION_NAV_BACK:
    #             if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
    #                 self.setFocusId(self.OPTIONS_GROUP_ID)
    #                 return

    #     except:
    #         util.ERROR()

    #     kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.exitCommand = 'HOME'
            self.doClose()
        elif controlID == self.EXTRA_LIST_ID:
            self.extrasListClicked()
        elif controlID == self.PLAY_BUTTON_ID:
            url = self.video.getStreamURL()
            util.DEBUG_LOG('Playing URL: {0}'.format(url))
            player.PLAYER.play(url)

    def extrasListClicked(self):
        mli = self.seasonListControl.getSelectedItem()
        if not mli:
            return

    def setInfo(self):
        self.setProperty('background', self.video.art.asTranscodedImageURL(1920, 1080, blur=128, opacity=60, background=colors.noAlpha.Background))
        self.setProperty('title', self.video.title)
        self.setProperty('duration', util.durationToText(self.video.duration.asInt()))
        self.setProperty('summary', self.video.summary)
        self.setProperty('thumb', self.video.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))

        directors = u' / '.join([d.tag for d in self.video.directors()])
        directorsLabel = len(self.video.directors) > 1 and u'DIRECTORS' or u'DIRECTOR'
        self.setProperty('directors', directors and u'{0}    {1}'.format(directorsLabel, directors) or '')

        writers = u' / '.join([w.tag for w in self.video.writers()])
        writersLabel = len(self.video.writers) > 1 and u'WRITERS' or u'WRITER'
        self.setProperty('writers', writers and u'{0}    {1}'.format(writersLabel, writers) or '')

        if self.video.audioStreams:
            self.setProperty('audio', self.video.audioStreams[0].getTitle())

        if self.video.subtitleStreams:
            self.setProperty('subtitles', self.video.subtitleStreams[0].getTitle())

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM), data_source=obj)
        return mli

    def fillExtras(self):
        return
        items = []
        idx = 0
        for extra in self.video.extras():
            mli = self.createListItem(extra)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.extraListControl.addItems(items)
