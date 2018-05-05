import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util
from lib import backgroundthread
from lib import metadata
from lib import player

from plexnet import plexapp, playlist, plexplayer

import busy
import videoplayer
import dropdown
import windowutils
import opener
import search
import playersettings
import info
import optionsdialog
import preplayutils

from lib.util import T


class EpisodeReloadTask(backgroundthread.Task):
    def setup(self, episode, callback):
        self.episode = episode
        self.callback = callback
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
            return

        try:
            self.episode.reload(checkFiles=1)
            if self.isCanceled():
                return
            self.callback(self.episode)
        except:
            util.ERROR()


class EpisodesWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-episodes.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_AR16X9_DIM = (657, 393)
    POSTER_DIM = (420, 630)
    RELATED_DIM = (268, 397)
    EXTRA_DIM = (329, 185)
    ROLES_DIM = (268, 268)

    EPISODE_LIST_ID = 400
    LIST_OPTIONS_BUTTON_ID = 111

    EXTRA_LIST_ID = 401
    RELATED_LIST_ID = 402
    ROLES_LIST_ID = 403

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    PROGRESS_IMAGE_ID = 250

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    INFO_BUTTON_ID = 304
    SETTINGS_BUTTON_ID = 305

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.reset(kwargs.get('episode'), kwargs.get('season'), kwargs.get('show'))
        self.parentList = kwargs.get('parentList')
        self.lastItem = None
        self.lastFocusID = None
        self.tasks = backgroundthread.Tasks()

    def reset(self, episode, season=None, show=None):
        self.episode = episode
        self.season = season or self.episode.season()
        self.show_ = show or self.season.show().reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
        self.parentList = None
        self.seasons = None

    def doClose(self):
        kodigui.ControlledWindow.doClose(self)
        if not self.tasks:
            return
        self.tasks.cancel()
        self.tasks = None
        player.PLAYER.off('new.video', self.onNewVideo)

    @busy.dialog()
    def onFirstInit(self):
        self.episodeListControl = kodigui.ManagedControlList(self, self.EPISODE_LIST_ID, 5)
        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)

        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)

        self._setup()
        self.postSetup()

    def onReInit(self):
        self.selectEpisode()

        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        self.reloadItems(items=[mli])

    def postSetup(self, from_select_episode=False):
        self.selectEpisode(from_select_episode=from_select_episode)
        self.checkForHeaderFocus(xbmcgui.ACTION_MOVE_DOWN)
        self.setFocusId(self.PLAY_BUTTON_ID)

    @busy.dialog()
    def setup(self):
        self._setup()

    def _setup(self):
        player.PLAYER.on('new.video', self.onNewVideo)
        self.season.reload(includeExtras=1, includeExtrasCount=10)
        self.updateProperties()
        self.fillEpisodes()
        hasPrev = self.fillExtras()
        hasPrev = self.fillRelated(hasPrev)
        self.fillRoles(hasPrev)

    def selectEpisode(self, from_select_episode=False):
        if not self.episode:
            return

        for mli in self.episodeListControl:
            if mli.dataSource == self.episode:
                self.episodeListControl.selectItem(mli.pos())
                break
        else:
            if not from_select_episode:
                self.reset(self.episode)
                self._setup()
                self.postSetup(from_select_episode=True)

        self.episode = None

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.next()
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.next()
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.prev()

            if controlID == self.EPISODE_LIST_ID:
                self.checkForHeaderFocus(action)
            if controlID == self.LIST_OPTIONS_BUTTON_ID and self.checkOptionsAction(action):
                return
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)) or not controlID:
                    if self.getProperty('on.extras'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.doClose()
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onNewVideo(self, video=None, **kwargs):
        if not video:
            return

        if not video.type == 'episode':
            return

        util.DEBUG_LOG('Updating selected episode: {0}'.format(video))
        self.episode = video

        return True

    def checkOptionsAction(self, action):
        if action == xbmcgui.ACTION_MOVE_UP:
            mli = self.episodeListControl.getSelectedItem()
            if not mli:
                return False
            pos = mli.pos() - 1
            if self.episodeListControl.positionIsValid(pos):
                self.setFocusId(self.EPISODE_LIST_ID)
                self.episodeListControl.selectItem(pos)
            return True
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            mli = self.episodeListControl.getSelectedItem()
            if not mli:
                return False
            pos = mli.pos() + 1
            if self.episodeListControl.positionIsValid(pos):
                self.setFocusId(self.EPISODE_LIST_ID)
                self.episodeListControl.selectItem(pos)
            return True

        return False

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.EPISODE_LIST_ID:
            self.episodeListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()

    def onFocus(self, controlID):
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item))

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
        if xbmc.getCondVisibility('Control.IsVisible(502)'):
            y += 520
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 125
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(502)'):
            y -= 500

        focus = int(xbmc.getInfoLabel('Container(403).Position'))

        x = ((focus + 1) * 304) - 100
        return x, y

    def getSeasons(self):
        if not self.seasons:
            self.seasons = self.season.show().seasons()

        if not self.seasons:
            return False

        return True

    def next(self):
        if not self._next():
            return
        self.setup()

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos += 1
            if pos >= len(self.seasons):
                pos = 0

            self.season = self.seasons[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos -= 1
            if pos < 0:
                pos = len(self.seasons) - 1

            self.season = self.seasons[pos]

        return True

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.season.getLibrarySectionId() or None))

    def playButtonClicked(self, shuffle=False):
        if shuffle:
            items = self.season.all()
            pl = playlist.LocalPlaylist(items, self.season.getServer())

            pl.shuffle(shuffle, first=True)
            videoplayer.play(play_queue=pl)
        else:
            self.episodeListClicked()

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def settingsButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        episode = mli.dataSource

        if not episode.mediaChoice:
            playerObject = plexplayer.PlexPlayer(episode)
            playerObject.build()
        playersettings.showDialog(video=episode, non_playback=True)
        self.setItemAudioAndSubtitleInfo(episode, mli)

    def infoButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        episode = mli.dataSource

        if episode.index:
            subtitle = u'{0} {1} {2} {3}'.format(T(32303, 'Season'), episode.parentIndex, T(32304, 'Episode'), episode.index)
        else:
            subtitle = episode.originallyAvailableAt.asDatetime('%B %d, %Y')

        opener.handleOpen(
            info.InfoWindow,
            title=episode.title,
            sub_title=subtitle,
            thumb=episode.thumb,
            thumb_fallback='script.plex/thumb_fallbacks/show.png',
            info=episode.summary,
            background=self.getProperty('background'),
            is_16x9=True
        )

    def episodeListClicked(self, play_version=False):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        episode = mli.dataSource

        if not episode.available():
            util.messageDialog(T(32312, 'unavailable'), T(32332, 'This item is currently unavailable.'))
            return

        if play_version:
            if not preplayutils.chooseVersion(episode):
                return
        else:
            preplayutils.resetVersion(episode)

        resume = False
        if episode.viewOffset.asInt():
            button = optionsdialog.show(
                T(32314, 'In Progress'),
                T(32315, 'Resume playback?'),
                T(32316, 'Resume'),
                T(32317, 'Play From Beginning')
            )

            if button is None:
                return

            resume = (button == 0)

        pl = playlist.LocalPlaylist(self.show_.all(), self.show_.getServer())
        if len(pl):  # Don't use playlist if it's only this video
            pl.setCurrent(episode)
            self.processCommand(videoplayer.play(play_queue=pl, resume=resume))
            return

        self.processCommand(videoplayer.play(video=episode, resume=resume))

    def optionsButtonClicked(self, from_item=False):
        options = []

        mli = self.episodeListControl.getSelectedItem()

        if mli:
            if len(mli.dataSource.media) > 1:
                options.append({'key': 'play_version', 'display': T(32451, 'Play Version...')})

            if mli.dataSource.isWatched and not mli.dataSource.viewOffset.asInt():
                options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unwatched')})
            else:
                options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Watched')})

            # if True:
            #     options.append({'key': 'add_to_playlist', 'display': '[COLOR FF808080]Add To Playlist[/COLOR]'})

        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        if self.season.isWatched:
            options.append({'key': 'mark_season_unwatched', 'display': T(32320, 'Mark Season Unwatched')})
        else:
            options.append({'key': 'mark_season_watched', 'display': T(32321, 'Mark Season Watched')})

        if mli.dataSource.server.allowsMediaDeletion:
            options.append({'key': 'delete', 'display': T(32322, 'Delete')})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        if options:
            options.append(dropdown.SEPARATOR)

        options.append({'key': 'to_show', 'display': T(32323, 'Go To Show')})
        options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.season.getLibrarySectionTitle())})

        pos = (500, 620)
        bottom = False
        setDropdownProp = False
        if from_item:
            viewPos = self.episodeListControl.getViewPosition()
            if viewPos > 6:
                pos = (1490, 312 + (viewPos * 100))
                bottom = True
            else:
                pos = (1490, 167 + (viewPos * 100))
                bottom = False
            setDropdownProp = True
        choice = dropdown.showDropdown(options, pos, pos_is_bottom=bottom, close_direction='top', set_dropdown_prop=setDropdownProp)
        if not choice:
            return

        if choice['key'] == 'play_version':
            self.episodeListClicked(play_version=True)
        elif choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            mli.dataSource.markWatched()
            self.updateItems(mli)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            mli.dataSource.markUnwatched()
            self.updateItems(mli)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_season_watched':
            self.season.markWatched()
            self.updateItems()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_season_unwatched':
            self.season.markUnwatched()
            self.updateItems()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.season.parentRatingKey))
        elif choice['key'] == 'to_section':
            self.goHome(self.season.getLibrarySectionId())
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

        if not self._delete():
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))

    @busy.dialog()
    def _delete(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        video = mli.dataSource
        success = video.delete()
        util.LOG('Media DELETE: {0} - {1}'.format(video, success and 'SUCCESS' or 'FAILED'))
        if success:
            self.episodeListControl.removeItem(mli.pos())
            if not self.episodeListControl.size():
                self.doClose()
            else:
                if self.season:
                    self.season.reload()
        return success

    def checkForHeaderFocus(self, action):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        if mli != self.lastItem:
            self.lastItem = mli
            self.setProgress(mli)

        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

    def updateProperties(self):
        showTitle = self.show_ and self.show_.title or ''

        self.setProperty(
            'background',
            (self.show_ or self.season.show()).art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('season.thumb', self.season.thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('show.title', showTitle)
        self.setProperty('season.title', self.season.title)
        self.setProperty('episodes.header', u'{0} \u2022 {1} {2}'.format(showTitle, T(32303, 'Season'), self.season.index))
        self.setProperty('extras.header', u'{0} \u2022 {1} {2}'.format(T(32305, 'Extras'), T(32303, 'Season'), self.season.index))
        self.setProperty('related.header', T(32306, 'Related Shows'))
        self.genre = self.show_.genres() and self.show_.genres()[0].tag or ''

    @busy.dialog()
    def updateItems(self, item=None):
        if item:
            item.setProperty('unwatched', not item.dataSource.isWatched and '1' or '')
            self.setProgress(item)
            self.season.reload()
        else:
            self.fillEpisodes(update=True)

        if self.episode:
            self.episode.reload()

    def setItemInfo(self, video, mli):
        # video.reload(checkFiles=1)
        mli.setProperty('background', video.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))
        mli.setProperty('title', video.title)
        mli.setProperty('show.title', video.grandparentTitle or (self.show_.title if self.show_ else ''))
        mli.setProperty('duration', util.durationToText(video.duration.asInt()))
        mli.setProperty('summary', video.summary.strip().replace('\t', ' '))

        if video.index:
            mli.setProperty('season', u'{0} {1}'.format(T(32303, 'Season'), video.parentIndex))
            mli.setProperty('episode', u'{0} {1}'.format(T(32304, 'Episode'), video.index))
        else:
            mli.setProperty('season', '')
            mli.setProperty('episode', '')

        mli.setProperty('date', util.cleanLeadingZeros(video.originallyAvailableAt.asDatetime('%B %d, %Y')))

        # mli.setProperty('related.header', 'Related Shows')
        mli.setProperty('year', video.year)
        mli.setProperty('content.rating', video.contentRating.split('/', 1)[-1])
        mli.setProperty('genre', self.genre)

        if video.get('userRating'):
            stars = str(int(round((video.userRating.asFloat() / 10) * 5)))
            mli.setProperty('rating.stars', stars)
        # elif video.rating:
        #     stars = str(int(round((video.rating.asFloat() / 10) * 5)))
        #     mli.setProperty('rating.stars', stars)

        if video.get('ratingImage'):
            rating = video.rating
            audienceRating = video.audienceRating
            if video.ratingImage.startswith('rottentomatoes:'):
                rating = '{0}%'.format(int(rating.asFloat() * 10))
                if audienceRating:
                    audienceRating = '{0}%'.format(int(audienceRating.asFloat() * 10))

            mli.setProperty('rating', rating)
            mli.setProperty('rating.image', 'script.plex/ratings/{0}.png'.format(video.ratingImage.replace('://', '/')))
            if video.get('audienceRatingImage'):
                mli.setProperty('rating2', audienceRating)
                mli.setProperty('rating2.image', 'script.plex/ratings/{0}.png'.format(video.audienceRatingImage.replace('://', '/')))
        else:
            mli.setProperty('rating', video.rating)

    def setPostReloadItemInfo(self, video, mli):
        self.setItemAudioAndSubtitleInfo(video, mli)
        mli.setProperty('unwatched', not video.isWatched and '1' or '')
        mli.setProperty('video.res', video.resolutionString())
        mli.setProperty('audio.codec', video.audioCodecString())
        mli.setProperty('audio.channels', video.audioChannelsString(metadata.apiTranslate))
        mli.setBoolProperty('unavailable', not video.available())

    def setItemAudioAndSubtitleInfo(self, video, mli):
        sas = video.selectedAudioStream()
        mli.setProperty('audio', sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None'))

        sss = video.selectedSubtitleStream()
        if sss:
            if len(video.subtitleStreams) > 1:
                mli.setProperty(
                    'subtitles', u'{0} \u2022 {1} {2}'.format(sss.getTitle(metadata.apiTranslate), len(video.subtitleStreams) - 1, T(32307, 'More'))
                )
            else:
                mli.setProperty('subtitles', sss.getTitle(metadata.apiTranslate))
        else:
            if video.subtitleStreams:
                mli.setProperty('subtitles', u'{0} \u2022 {1} {2}'.format(T(32309, 'None'), len(video.subtitleStreams), T(32308, 'Available')))
            else:
                mli.setProperty('subtitles', T(32309, 'None'))

    def setProgress(self, mli):
        video = mli.dataSource

        if video.viewOffset.asInt():
            width = video.viewOffset.asInt() and (1 + int((video.viewOffset.asInt() / video.duration.asFloat()) * self.width)) or 1
            self.progressImageControl.setWidth(width)
        else:
            self.progressImageControl.setWidth(1)

    def createListItem(self, episode):
        if episode.index:
            subtitle = u'{0}{1} \u2022 {2}{3}'.format(T(32310, 'S'), episode.parentIndex, T(32311, 'E'), episode.index)
        else:
            subtitle = episode.originallyAvailableAt.asDatetime('%m/%d/%y')

        mli = kodigui.ManagedListItem(
            episode.title,
            subtitle,
            thumbnailImage=episode.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM),
            data_source=episode
        )
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        mli.setProperty('episode.number', str(episode.index) or '')
        mli.setProperty('episode.duration', util.durationToText(episode.duration.asInt()))
        mli.setProperty('unwatched', not episode.isWatched and '1' or '')
        # mli.setProperty('progress', util.getProgressImage(obj))
        return mli

    def fillEpisodes(self, update=False):
        items = []
        idx = 0

        episodes = self.season.episodes()
        self.episodeListControl.addItems(
            [kodigui.ManagedListItem(properties={'thumb.fallback': 'script.plex/thumb_fallbacks/show.png'}) for x in range(len(episodes))]
        )

        if self.episode and self.episode in episodes:
            self.episodeListControl.selectItem(episodes.index(self.episode))

        for episode in episodes:
            mli = self.createListItem(episode)
            self.setItemInfo(episode, mli)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.episodeListControl.replaceItems(items)

        self.reloadItems(items)

    def reloadItems(self, items):
        tasks = []
        for mli in items:
            task = EpisodeReloadTask().setup(mli.dataSource, self.reloadItemCallback)
            self.tasks.add(task)
            tasks.append(task)

        backgroundthread.BGThreader.addTasks(tasks)

    def reloadItemCallback(self, episode):
        selected = self.episodeListControl.getSelectedItem()

        for mli in self.episodeListControl:
            if mli.dataSource == episode:
                self.setPostReloadItemInfo(episode, mli)
                if mli == selected:
                    self.setProgress(mli)
                return

    def fillExtras(self):
        items = []
        idx = 0

        if not self.season.extras:
            self.extraListControl.reset()
            return False

        for extra in self.season.extras():
            mli = kodigui.ManagedListItem(
                extra.title or '',
                metadata.EXTRA_MAP.get(extra.extraType.asInt(), ''),
                thumbnailImage=extra.thumb.asTranscodedImageURL(*self.EXTRA_DIM),
                data_source=extra
            )

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

        if not self.show_.related:
            self.relatedListControl.reset()
            return has_prev

        self.setProperty('divider.{0}'.format(self.RELATED_LIST_ID), has_prev and '1' or '')

        for rel in self.show_.related()[0].items:
            mli = kodigui.ManagedListItem(
                rel.title or '',
                thumbnailImage=rel.defaultThumb.asTranscodedImageURL(*self.RELATED_DIM),
                data_source=rel
            )
            if mli:
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(rel.type in ('show', 'season', 'episode') and 'show' or 'movie'))
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.relatedListControl.reset()
        self.relatedListControl.addItems(items)
        return True

    def fillRoles(self, has_prev=False):
        items = []
        idx = 0

        if not self.show_.roles:
            self.rolesListControl.reset()
            return False

        for role in self.show_.roles():
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
