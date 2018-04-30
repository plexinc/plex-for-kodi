import xbmc
import xbmcgui
import kodigui

import busy
import opener
import info
import videoplayer
import playersettings
import search
import dropdown
import windowutils
import optionsdialog
import preplayutils

from plexnet import plexplayer, media

from lib import colors
from lib import util
from lib import metadata

from lib.util import T


class PrePlayWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
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
    SEARCH_BUTTON_ID = 202

    INFO_BUTTON_ID = 304
    PLAY_BUTTON_ID = 302
    TRAILER_BUTTON_ID = 303
    SETTINGS_BUTTON_ID = 305
    OPTIONS_BUTTON_ID = 306

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.auto_play = kwargs.get('auto_play')
        self.parentList = kwargs.get('parent_list')
        self.videos = None
        self.exitCommand = None
        self.trailer = None
        self.lastFocusID = None

    def onFirstInit(self):
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)

        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)
        self.setup()

        if self.auto_play:
            self.auto_play = False
            self.playVideo()

    def onReInit(self):
        self.video.reload()
        self.refreshInfo()

    def refreshInfo(self):
        oldFocusId = self.getFocusId()

        util.setGlobalProperty('hide.resume', '' if self.video.viewOffset.asInt() else '1')
        self.setInfo()
        xbmc.sleep(100)

        if oldFocusId == self.PLAY_BUTTON_ID:
            self.focusPlayButton()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    if self.getProperty('on.extras'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.next()
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.setFocusId(300)
                self.next()
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.setFocusId(300)
                self.prev()
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()
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
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def onFocus(self, controlID):
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.video.getLibrarySectionId() or None))

    def settingsButtonClicked(self):
        if not self.video.mediaChoice:
            playerObject = plexplayer.PlexPlayer(self.video)
            playerObject.build()
        playersettings.showDialog(video=self.video, non_playback=True)
        self.setAudioAndSubtitleInfo()

    def infoButtonClicked(self):
        opener.handleOpen(
            info.InfoWindow,
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

        if len(self.video.media) > 1:
            options.append({'key': 'play_version', 'display': T(32451, 'Play Version...')})

        if self.video.isWatched and not self.video.viewOffset.asInt():
            options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unwatched')})
        else:
            options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Watched')})

        options.append(dropdown.SEPARATOR)

        if self.video.type == 'episode':
            options.append({'key': 'to_season', 'display': T(32400, 'Go to Season')})
            options.append({'key': 'to_show', 'display': T(32323, 'Go to Show')})

        if self.video.type in ('episode', 'movie'):
            options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.video.getLibrarySectionTitle())})

        if self.video.server.allowsMediaDeletion:
            options.append({'key': 'delete', 'display': T(32322, 'Delete')})
        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})
        posy = 880
        if not util.getGlobalProperty('hide.resume'):
            posy += 106
        if self.getProperty('trailer.button'):
            posy += 106
        choice = dropdown.showDropdown(options, (posy, 618), close_direction='left')
        if not choice:
            return

        if choice['key'] == 'play_version':
            self.playVideo(play_version=True)
        elif choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.video.markWatched()
            self.refreshInfo()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            self.video.markUnwatched()
            self.refreshInfo()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_season':
            self.processCommand(opener.open(self.video.parentRatingKey))
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.video.grandparentRatingKey))
        elif choice['key'] == 'to_section':
            self.goHome(self.video.getLibrarySectionId())
        elif choice['key'] == 'delete':
            self.delete()

    def delete(self):
        button = optionsdialog.show(
            T(32326, 'Really delete?'),
            T(32327, 'Are you sure you really want to delete this media?'),
            T(32328, 'Yes'),
            T(32329, 'No')
        )

        if button != 0:
            return

        if self._delete():
            self.doClose()
        else:
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))

    @busy.dialog()
    def _delete(self):
        success = self.video.delete()
        util.LOG('Media DELETE: {0} - {1}'.format(self.video, success and 'SUCCESS' or 'FAILED'))
        return success

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

    def getVideos(self):
        if not self.videos:
            if self.video.TYPE == 'episode':
                self.videos = self.video.show().episodes()

        if not self.videos:
            return False

        return True

    def next(self):
        if not self._next():
            return
        self.setup()

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.video)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.video = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getVideos():
                return False

            if self.video not in self.videos:
                return False

            pos = self.videos.index(self.video)
            pos += 1
            if pos >= len(self.videos):
                pos = 0

            self.video = self.videos[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.video)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.video = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getVideos():
                return False

            if self.video not in self.videos:
                return False

            pos = self.videos.index(self.video)
            pos -= 1
            if pos < 0:
                pos = len(self.videos) - 1

            self.video = self.videos[pos]

        return True

    def getRoleItemDDPosition(self):
        y = 980
        if xbmc.getCondVisibility('Control.IsVisible(500)'):
            y += 360
        if xbmc.getCondVisibility('Control.IsVisible(501)'):
            y += 520
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 300
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)'):
            y -= 500

        focus = int(xbmc.getInfoLabel('Container(403).Position'))

        x = ((focus + 1) * 304) - 100
        return x, y

    def playVideo(self, play_version=False):
        if not self.video.available():
            util.messageDialog(T(32312, 'Unavailable'), T(32313, 'This item is currently unavailable.'))
            return

        if play_version:
            if not preplayutils.chooseVersion(self.video):
                return
        else:
            preplayutils.resetVersion(self.video)

        resume = False
        if self.video.viewOffset.asInt():
            button = optionsdialog.show(
                T(32314, 'In Progress'),
                T(32315, 'Resume playback?'),
                T(32316, 'Resume'),
                T(32317, 'Play From Beginning')
            )

            if button is None:
                return

            resume = (button == 0)

        self.processCommand(videoplayer.play(video=self.video, resume=resume))

    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item))

    def focusPlayButton(self):
        try:
            if not self.getFocusId() == self.PLAY_BUTTON_ID:
                self.setFocusId(self.PLAY_BUTTON_ID)
        except (SystemError, RuntimeError):
            self.setFocusId(self.PLAY_BUTTON_ID)

    @busy.dialog()
    def setup(self):
        self.focusPlayButton()

        util.DEBUG_LOG('PrePlay: Showing video info: {0}'.format(self.video))
        if self.video.type == 'episode':
            self.setProperty('preview.yes', '1')
        elif self.video.type == 'movie':
            self.setProperty('preview.no', '1')

        self.video.reload(checkFiles=1, includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
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
        directorsLabel = len(self.video.directors) > 1 and T(32401, u'DIRECTORS').upper() or T(32383, u'DIRECTOR').upper()
        self.setProperty('directors', directors and u'{0}    {1}'.format(directorsLabel, directors) or '')

        if self.video.type == 'episode':
            self.setProperty('content.rating', '')
            self.setProperty('thumb', self.video.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            self.setProperty('preview', self.video.thumb.asTranscodedImageURL(*self.PREVIEW_DIM))
            self.setProperty('info', u'{0} {1} {2} {3}'.format(T(32303, 'Season'), self.video.parentIndex, T(32304, 'Episode'), self.video.index))
            self.setProperty('date', util.cleanLeadingZeros(self.video.originallyAvailableAt.asDatetime('%B %d, %Y')))

            writers = u' / '.join([w.tag for w in self.video.writers()][:5])
            writersLabel = len(self.video.writers) > 1 and T(32403, u'WRITERS').upper() or T(32402, u'WRITER').upper()
            self.setProperty('writers', writers and u'{0}    {1}'.format(writersLabel, writers) or '')
            self.setProperty('related.header', T(32306, 'Related Shows'))
        elif self.video.type == 'movie':
            self.setProperty('preview', '')
            self.setProperty('thumb', self.video.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            genres = u' / '.join([g.tag for g in self.video.genres()][:3])
            self.setProperty('info', genres)
            self.setProperty('date', self.video.year)
            self.setProperty('content.rating', self.video.contentRating.split('/', 1)[-1])

            cast = u' / '.join([r.tag for r in self.video.roles()][:5])
            castLabel = 'CAST'
            self.setProperty('writers', cast and u'{0}    {1}'.format(castLabel, cast) or '')
            self.setProperty('related.header', T(32404, 'Related Movies'))

        self.setProperty('video.res', self.video.resolutionString())
        self.setProperty('audio.codec', self.video.audioCodecString())
        self.setProperty('audio.channels', self.video.audioChannelsString(metadata.apiTranslate))

        self.setProperties(('rating.stars', 'rating', 'rating.image', 'rating2', 'rating2.image'), '')
        if self.video.userRating:
            stars = str(int(round((self.video.userRating.asFloat() / 10) * 5)))
            self.setProperty('rating.stars', stars)
        # elif self.video.rating:
        #     stars = str(int(round((self.video.rating.asFloat() / 10) * 5)))
        #     self.setProperty('rating.stars', stars)

        if self.video.ratingImage:
            rating = self.video.rating
            audienceRating = self.video.audienceRating
            if self.video.ratingImage.startswith('rottentomatoes:'):
                rating = '{0}%'.format(int(rating.asFloat() * 10))
                if audienceRating:
                    audienceRating = '{0}%'.format(int(audienceRating.asFloat() * 10))

            self.setProperty('rating', rating)
            self.setProperty('rating.image', 'script.plex/ratings/{0}.png'.format(self.video.ratingImage.replace('://', '/')))
            if self.video.audienceRatingImage:
                self.setProperty('rating2', audienceRating)
                self.setProperty('rating2.image', 'script.plex/ratings/{0}.png'.format(self.video.audienceRatingImage.replace('://', '/')))
        else:
            self.setProperty('rating', self.video.rating)

        self.setAudioAndSubtitleInfo()

        self.setProperty('unavailable', not self.video.media()[0].isAccessible() and '1' or '')

        if self.video.viewOffset.asInt():
            width = self.video.viewOffset.asInt() and (1 + int((self.video.viewOffset.asInt() / self.video.duration.asFloat()) * self.width)) or 1
            self.progressImageControl.setWidth(width)
        else:
            self.progressImageControl.setWidth(1)

    def setAudioAndSubtitleInfo(self):
        sas = self.video.selectedAudioStream()
        self.setProperty('audio', sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None'))

        sss = self.video.selectedSubtitleStream()
        if sss:
            if len(self.video.subtitleStreams) > 1:
                self.setProperty(
                    'subtitles', u'{0} \u2022 {1} {2}'.format(sss.getTitle(metadata.apiTranslate), len(self.video.subtitleStreams) - 1, T(32307, 'More'))
                )
            else:
                self.setProperty('subtitles', sss.getTitle(metadata.apiTranslate))
        else:
            if self.video.subtitleStreams:
                self.setProperty('subtitles', u'{0} \u2022 {1} {2}'.format(T(32309, 'None'), len(self.video.subtitleStreams), T(32308, 'Available')))
            else:
                self.setProperty('subtitles', T(32309, u'None'))

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumb.asTranscodedImageURL(*self.EXTRA_DIM), data_source=obj)
        return mli

    def fillExtras(self):
        items = []
        idx = 0

        if not self.video.extras:
            self.extraListControl.reset()
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

        self.extraListControl.reset()
        self.extraListControl.addItems(items)
        return True

    def fillRelated(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.related:
            self.relatedListControl.reset()
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

        self.relatedListControl.reset()
        self.relatedListControl.addItems(items)
        return True

    def fillRoles(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.roles:
            self.rolesListControl.reset()
            return False

        for role in self.video.roles():
            mli = kodigui.ManagedListItem(role.tag, role.role, thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM), data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.setProperty('divider.{0}'.format(self.ROLES_LIST_ID), has_prev and '1' or '')

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True
