import xbmc
import xbmcgui
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
    PREVIEW_DIM = (343, 193)

    EXTRA_LIST_ID = 101
    OPTIONS_GROUP_ID = 200
    PROGRESS_IMAGE_ID = 500

    HOME_BUTTON_ID = 201
    RESUME_BUTTON_ID = 301
    PLAY_BUTTON_ID = 302

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.exitCommand = None

    def onFirstInit(self):
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)
        self.setInfo()
        self.fillExtras()
        # import xbmc
        # xbmc.sleep(100)
        # if self.video.viewOffset.asInt():
        #     self.setFocusId(self.RESUME_BUTTON_ID)
        # else:
        #     self.setFocusId(self.PLAY_BUTTON_ID)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return

        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.exitCommand = 'HOME'
            self.doClose()
        elif controlID == self.EXTRA_LIST_ID:
            self.extrasListClicked()
        elif controlID == self.RESUME_BUTTON_ID:
            self.playVideo(resume=True)
        elif controlID == self.PLAY_BUTTON_ID:
            self.playVideo()

    def playVideo(self, resume=False):
        player.PLAYER.playVideo(self.video, resume)

    def extrasListClicked(self):
        mli = self.seasonListControl.getSelectedItem()
        if not mli:
            return

    def setInfo(self):
        util.DEBUG_LOG('PrePlay: Showing video info: {0}'.format(self.video))
        self.video.reload()

        self.setProperty('background', self.video.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))
        self.setProperty('title', self.video.title)
        self.setProperty('duration', util.durationToText(self.video.duration.asInt()))
        self.setProperty('summary', self.video.summary)

        directors = u' / '.join([d.tag for d in self.video.directors()])
        directorsLabel = len(self.video.directors) > 1 and u'DIRECTORS' or u'DIRECTOR'
        self.setProperty('directors', directors and u'{0}    {1}'.format(directorsLabel, directors) or '')

        if self.video.type == 'episode':
            self.setProperty('thumb', self.video.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            self.setProperty('preview', self.video.thumb.asTranscodedImageURL(*self.PREVIEW_DIM))
            self.setProperty('info', 'Season {0} Episode {1}'.format(self.video.parentIndex, self.video.index))
            self.setProperty('date', util.cleanLeadingZeros(self.video.originallyAvailableAt.asDatetime('%B %d, %Y')))

            writers = u' / '.join([w.tag for w in self.video.writers()])
            writersLabel = len(self.video.writers) > 1 and u'WRITERS' or u'WRITER'
            self.setProperty('writers', writers and u'{0}    {1}'.format(writersLabel, writers) or '')
        elif self.video.type == 'movie':
            self.setProperty('thumb', self.video.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            genres = u' / '.join([g.tag for g in self.video.genres()])
            self.setProperty('info', genres)
            self.setProperty('date', self.video.year)
            self.setProperty('content.rating', self.video.contentRating)

            cast = u' / '.join([r.tag for r in self.video.roles()])
            castLabel = 'CAST'
            self.setProperty('writers', cast and u'{0}    {1}'.format(castLabel, cast) or '')

        stars = self.video.rating and str(int(round((self.video.rating.asFloat() / 10) * 5))) or None
        self.setProperty('rating', stars and stars or '')

        sas = self.video.selectedAudioStream()
        self.setProperty('audio', sas and sas.getTitle() or 'None')

        sss = self.video.selectedSubtitleStream()
        self.setProperty('subtitles', sss and sss.getTitle() or 'None')

        if self.video.viewOffset.asInt():
            width = self.video.viewOffset.asInt() and (1 + int((self.video.viewOffset.asInt() / self.video.duration.asFloat()) * self.width)) or 1
            self.progressImageControl.setWidth(width)
        else:
            self.setProperty('hide.resume', '1')

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
