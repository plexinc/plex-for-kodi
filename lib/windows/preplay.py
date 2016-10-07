import xbmc
import xbmcgui
import kodigui

import busy
import opener
import info
import videoplayer
import playersettings
import dropdown
import windowutils
from plexnet import plexplayer, media

from lib import colors
from lib import util


class PrePlayWindow(kodigui.BaseWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-pre_play.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_POSTER_DIM = (347, 518)
    RELATED_DIM = (268, 397)
    EXTRA_DIM = (329, 185)
    ROLES_DIM = (268, 268)
    PREVIEW_DIM = (343, 193)

    EXTRA_LIST_ID = 400
    RELATED_LIST_ID = 401
    ROLES_LIST_ID = 403

    OPTIONS_GROUP_ID = 200
    PROGRESS_IMAGE_ID = 250

    HOME_BUTTON_ID = 201

    INFO_BUTTON_ID = 304
    RESUME_BUTTON_ID = 301
    PLAY_BUTTON_ID = 302
    TRAILER_BUTTON_ID = 303
    SETTINGS_BUTTON_ID = 305
    OPTIONS_BUTTON_ID = 306

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.exitCommand = None
        self.trailer = None

    def onFirstInit(self):
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)

        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)
        self.setup()
        # import xbmc
        # xbmc.sleep(100)
        if self.video.viewOffset.asInt():
            self.setFocusId(self.RESUME_BUTTON_ID)
        # else:
        #     self.setFocusId(self.PLAY_BUTTON_ID)

    def onReInit(self):
        self.video.reload()
        self.setInfo()

    def onAction(self, action):
        try:
            if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.closeWithCommand('HOME')
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()
        elif controlID == self.RESUME_BUTTON_ID:
            self.playVideo(resume=True)
        elif controlID == self.PLAY_BUTTON_ID:
            self.playVideo()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.TRAILER_BUTTON_ID:
            self.openItem(item=self.trailer)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()

    def onFocus(self, controlID):
        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def settingsButtonClicked(self):
        if not self.video.mediaChoice:
            playerObject = plexplayer.PlexPlayer(self.video)
            playerObject.build()
        playersettings.showDialog(video=self.video, non_playback=True)

    def infoButtonClicked(self):
        info.InfoWindow.open(
            title=self.video.title,
            sub_title=self.getProperty('info'),
            thumb=self.video.type == 'episode' and self.video.thumb or self.video.defaultThumb,
            thumb_fallback='script.plex/thumb_fallbacks/{0}.png'.format(self.video.type == 'episode' and 'show' or 'movie'),
            info=self.video.summary,
            background=self.getProperty('background'),
            is_16x9=self.video.type == 'episode'
        )

    def optionsButtonClicked(self):
        options = []
        # if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
        #     options.append({'key': 'play_next', 'display': 'Play Next'})

        if self.video.isWatched:
            options.append({'key': 'mark_unwatched', 'display': 'Mark Unwatched'})
        else:
            options.append({'key': 'mark_watched', 'display': 'Mark Watched'})

        options.append(dropdown.SEPARATOR)

        if self.video.type == 'episode':
            options.append({'key': 'to_season', 'display': 'Go to Season'})
            options.append({'key': 'to_show', 'display': 'Go to Show'})

        if self.video.type in ('episode', 'movie'):
            options.append({'key': 'to_section', 'display': u'Go to {0}'.format(self.video.getLibrarySectionTitle())})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})
        posy = 880
        if not self.getProperty('hide.resume'):
            posy += 106
        if self.getProperty('trailer.button'):
            posy += 106
        choice = dropdown.showDropdown(options, (posy, 618), close_direction='left')
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.video.markWatched()
            self.setInfo()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            self.video.markUnwatched()
            self.setInfo()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_season':
            self.processCommand(opener.open(self.video.parentRatingKey))
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.video.grandparentRatingKey))
        elif choice['key'] == 'to_section':
            self.closeWithCommand('HOME:{0}'.format(self.video.getLibrarySectionId()))

    def roleClicked(self):
        mli = self.rolesListControl.getSelectedItem()
        if not mli:
            return

        sectionRoles = busy.widthDialog(mli.dataSource.sectionRoles, '')

        if not sectionRoles:
            util.DEBUG_LOG('No sections found for actor')
            return

        if len(sectionRoles) > 1:
            x, y = self.getRoleItemDDPosition()

            options = [{'role': r, 'display': r.reasonTitle} for r in sectionRoles]
            choice = dropdown.showDropdown(options, (x, y), pos_is_bottom=True, close_direction='bottom')

            if not choice:
                return

            role = choice['role']
        else:
            role = sectionRoles[0]

        self.processCommand(opener.open(role))

    def getRoleItemDDPosition(self):
        y = 980
        if xbmc.getCondVisibility('Control.IsVisible(500)'):
            y += 360
        if xbmc.getCondVisibility('Control.IsVisible(501)'):
            y += 520
        if xbmc.getCondVisibility('!IsEmpty(Window.Property(on.extras))'):
            y -= 300
        if xbmc.getCondVisibility('IntegerGreaterThan(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 500
        if xbmc.getCondVisibility('IntegerGreaterThan(Window.Property(hub.focus),1) + Control.IsVisible(501)'):
            y -= 500

        focus = int(xbmc.getInfoLabel('Container(403).Position'))

        x = ((focus + 1) * 304) - 100
        return x, y

    def playVideo(self, resume=False):
        videoplayer.play(video=self.video, resume=resume)

    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item))

    @busy.dialog()
    def setup(self):
        util.DEBUG_LOG('PrePlay: Showing video info: {0}'.format(self.video))
        if self.video.type == 'episode':
            self.setProperty('preview.yes', '1')
        elif self.video.type == 'movie':
            self.setProperty('preview.no', '1')

        self.video.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
        self.setInfo()
        self.fillExtras()
        hasPrev = self.fillRelated()
        self.fillRoles(hasPrev)

    def setInfo(self):
        self.setProperty('background', self.video.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))
        self.setProperty('title', self.video.title)
        self.setProperty('duration', util.durationToText(self.video.duration.asInt()))
        self.setProperty('summary', self.video.summary.strip().replace('\t', ' '))

        directors = u' / '.join([d.tag for d in self.video.directors()][:5])
        directorsLabel = len(self.video.directors) > 1 and u'DIRECTORS' or u'DIRECTOR'
        self.setProperty('directors', directors and u'{0}    {1}'.format(directorsLabel, directors) or '')

        if self.video.type == 'episode':
            self.setProperty('thumb', self.video.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            self.setProperty('preview', self.video.thumb.asTranscodedImageURL(*self.PREVIEW_DIM))
            self.setProperty('info', 'Season {0} Episode {1}'.format(self.video.parentIndex, self.video.index))
            self.setProperty('date', util.cleanLeadingZeros(self.video.originallyAvailableAt.asDatetime('%B %d, %Y')))

            writers = u' / '.join([w.tag for w in self.video.writers()][:5])
            writersLabel = len(self.video.writers) > 1 and u'WRITERS' or u'WRITER'
            self.setProperty('writers', writers and u'{0}    {1}'.format(writersLabel, writers) or '')
            self.setProperty('related.header', 'Related Shows')
        elif self.video.type == 'movie':
            self.setProperty('thumb', self.video.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            genres = u' / '.join([g.tag for g in self.video.genres()][:3])
            self.setProperty('info', genres)
            self.setProperty('date', self.video.year)
            self.setProperty('content.rating', self.video.contentRating)

            cast = u' / '.join([r.tag for r in self.video.roles()][:5])
            castLabel = 'CAST'
            self.setProperty('writers', cast and u'{0}    {1}'.format(castLabel, cast) or '')
            self.setProperty('related.header', 'Related Movies')

        stars = self.video.rating and str(int(round((self.video.rating.asFloat() / 10) * 5))) or None
        self.setProperty('rating', stars and stars or '')

        self.setProperty('imdb', self.video.rating)

        sas = self.video.selectedAudioStream()
        self.setProperty('audio', sas and sas.getTitle() or 'None')

        sss = self.video.selectedSubtitleStream()
        self.setProperty('subtitles', sss and sss.getTitle() or 'None')

        self.setProperty('unavailable', not self.video.media()[0].isAccessible() and '1' or '')

        if self.video.viewOffset.asInt():
            width = self.video.viewOffset.asInt() and (1 + int((self.video.viewOffset.asInt() / self.video.duration.asFloat()) * self.width)) or 1
            self.progressImageControl.setWidth(width)
            self.setProperty('hide.resume', '')
        else:
            self.progressImageControl.setWidth(1)
            self.setProperty('hide.resume', '1')

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumb.asTranscodedImageURL(*self.EXTRA_DIM), data_source=obj)
        return mli

    def fillExtras(self):
        items = []
        idx = 0

        if not self.video.extras:
            return False

        for extra in self.video.extras():
            if not self.trailer and extra.extraType.asInt() == media.METADATA_RELATED_TRAILER:
                self.trailer = extra
                self.setProperty('trailer.button', '1')
                continue

            mli = self.createListItem(extra)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty(
                    'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(extra.type in ('show', 'season', 'episode') and 'show' or 'movie')
                )
                items.append(mli)
                idx += 1

        if not items:
            return False

        self.extraListControl.addItems(items)
        return True

    def fillRelated(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.related:
            return False

        for rel in self.video.related()[0].items:
            mli = kodigui.ManagedListItem(rel.title or '', thumbnailImage=rel.thumb.asTranscodedImageURL(*self.RELATED_DIM), data_source=rel)
            if mli:
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(rel.type in ('show', 'season', 'episode') and 'show' or 'movie'))
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        if not items:
            return False

        self.setProperty('divider.{0}'.format(self.RELATED_LIST_ID), has_prev and '1' or '')

        self.relatedListControl.addItems(items)
        return True

    def fillRoles(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.roles:
            return False

        for role in self.video.roles():
            mli = kodigui.ManagedListItem(role.tag, role.role, thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM), data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.setProperty('divider.{0}'.format(self.ROLES_LIST_ID), has_prev and '1' or '')

        self.rolesListControl.addItems(items)
        return True
