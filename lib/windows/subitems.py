import gc

import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util
from lib import metadata

from plexnet import playlist

import busy
import episodes
import tracks
import opener
import info
import musicplayer
import videoplayer
import dropdown
import windowutils
import search

from lib.util import T


class ShowWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-seasons.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_DIMS = {
        'show': {
            'main.thumb': (347, 518),
            'item.thumb': (174, 260)
        },
        'episode': {
            'main.thumb': (347, 518),
            'item.thumb': (198, 295)
        },
        'artist': {
            'main.thumb': (519, 519),
            'item.thumb': (215, 215)
        }
    }

    EXTRA_DIM = (329, 185)
    RELATED_DIM = (268, 397)
    ROLES_DIM = (268, 268)

    SUB_ITEM_LIST_ID = 400

    EXTRA_LIST_ID = 401
    RELATED_LIST_ID = 402
    ROLES_LIST_ID = 403

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    PROGRESS_IMAGE_ID = 250

    INFO_BUTTON_ID = 301
    PLAY_BUTTON_ID = 302
    SHUFFLE_BUTTON_ID = 303
    OPTIONS_BUTTON_ID = 304

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.mediaItem = kwargs.get('media_item')
        self.parentList = kwargs.get('parent_list')
        self.mediaItems = None
        self.exitCommand = None
        self.lastFocusID = None

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)

        self.setup()

        self.setFocusId(self.PLAY_BUTTON_ID)

    def setup(self):
        self.mediaItem.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)

        self.updateProperties()
        self.fill()
        hasPrev = self.fillExtras()
        hasPrev = self.fillRelated(hasPrev)
        self.fillRoles(hasPrev)

    def updateProperties(self):
        self.setProperty('title', self.mediaItem.title)
        self.setProperty('summary', self.mediaItem.summary)
        self.setProperty('thumb', self.mediaItem.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['main.thumb']))
        self.setProperty(
            'background',
            self.mediaItem.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('duration', util.durationToText(self.mediaItem.fixedDuration()))
        self.setProperty('info', '')
        self.setProperty('date', self.mediaItem.year)

        self.setProperty('extras.header', T(32305, 'Extras'))
        self.setProperty('related.header', T(32306, 'Related Shows'))

        if self.mediaItem.creator:
            self.setProperty('directors', u'{0}    {1}'.format(T(32418, 'Creator').upper(), self.mediaItem.creator))
        elif self.mediaItem.studio:
            self.setProperty('directors', u'{0}    {1}'.format(T(32386, 'Studio').upper(), self.mediaItem.studio))

        cast = u' / '.join([r.tag for r in self.mediaItem.roles()][:5])
        castLabel = T(32419, 'Cast').upper()
        self.setProperty('writers', cast and u'{0}    {1}'.format(castLabel, cast) or '')

        genres = self.mediaItem.genres()
        self.setProperty('info', genres and (u' / '.join([g.tag for g in genres][:3])) or '')

        self.setProperties(('rating.stars', 'rating', 'rating.image', 'rating2', 'rating2.image'), '')

        if self.mediaItem.userRating:
            stars = str(int(round((self.mediaItem.userRating.asFloat() / 10) * 5)))
            self.setProperty('rating.stars', stars)

        if self.mediaItem.ratingImage:
            rating = self.mediaItem.rating
            audienceRating = self.mediaItem.audienceRating
            if self.mediaItem.ratingImage.startswith('rottentomatoes:'):
                rating = '{0}%'.format(int(rating.asFloat() * 10))
                if audienceRating:
                    audienceRating = '{0}%'.format(int(audienceRating.asFloat() * 10))

            self.setProperty('rating', rating)
            self.setProperty('rating.image', 'script.plex/ratings/{0}.png'.format(self.mediaItem.ratingImage.replace('://', '/')))
            if self.mediaItem.audienceRatingImage:
                self.setProperty('rating2', audienceRating)
                self.setProperty('rating2.image', 'script.plex/ratings/{0}.png'.format(self.mediaItem.audienceRatingImage.replace('://', '/')))
        else:
            self.setProperty('rating', self.mediaItem.rating)

        sas = self.mediaItem.selectedAudioStream()
        self.setProperty('audio', sas and sas.getTitle() or 'None')

        sss = self.mediaItem.selectedSubtitleStream()
        self.setProperty('subtitles', sss and sss.getTitle() or 'None')

        leafcount = self.mediaItem.leafCount.asFloat()
        if leafcount:
            width = (int((self.mediaItem.viewedLeafCount.asInt() / leafcount) * self.width)) or 1
            self.progressImageControl.setWidth(width)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
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
        elif controlID == self.SUB_ITEM_LIST_ID:
            self.subItemListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
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

    def getMediaItems(self):
        return False

    def next(self):
        if not self._next():
            return
        self.setup()

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.mediaItem)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.mediaItem = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getMediaItems():
                return False

            if self.mediaItem not in self.mediaItems:
                return False

            pos = self.mediaItems.index(self.mediaItem)
            pos += 1
            if pos >= len(self.mediaItems):
                pos = 0

            self.mediaItem = self.mediaItems[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.mediaItem)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.mediaItem = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getMediaItems():
                return False

            if self.mediaItem not in self.mediaItems:
                return False

            pos = self.mediaItems.index(self.mediaItem)
            pos -= 1
            if pos < 0:
                pos = len(self.mediaItems) - 1

            self.mediaItem = self.mediaItems[pos]

        return True

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.mediaItem.getLibrarySectionId() or None))

    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item))

    def subItemListClicked(self):
        mli = self.subItemListControl.getSelectedItem()
        if not mli:
            return

        update = False

        w = None
        if self.mediaItem.type == 'show':
            w = episodes.EpisodesWindow.open(season=mli.dataSource, show=self.mediaItem, parent_list=self.subItemListControl)
            update = True
        elif self.mediaItem.type == 'artist':
            w = tracks.AlbumWindow.open(album=mli.dataSource, parent_list=self.subItemListControl)

        if not mli.dataSource.exists():
            self.subItemListControl.removeItem(mli.pos())

        if not self.subItemListControl.size():
            self.closeWithCommand(w.exitCommand)
            del w
            gc.collect(2)
            return

        if update:
            mli.setProperty('unwatched.count', not mli.dataSource.isWatched and str(mli.dataSource.unViewedLeafCount) or '')
            self.mediaItem.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
            self.updateProperties()

        try:
            self.processCommand(w.exitCommand)
        finally:
            del w
            gc.collect(2)

    def infoButtonClicked(self):
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(self.mediaItem.type == 'show' and 'show' or 'music')
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])
        w = info.InfoWindow.open(
            title=self.mediaItem.title,
            sub_title=genres,
            thumb=self.mediaItem.defaultThumb,
            thumb_fallback=fallback,
            info=self.mediaItem.summary,
            background=self.getProperty('background'),
            is_square=bool(isinstance(self, ArtistWindow))
        )
        del w
        util.garbageCollect()

    def playButtonClicked(self, shuffle=False):
        items = self.mediaItem.all()
        pl = playlist.LocalPlaylist(items, self.mediaItem.getServer())
        resume = False
        if not shuffle and self.mediaItem.type == 'show':
            resume = self.getPlaylistResume(pl, items, self.mediaItem.title)
            if resume is None:
                return

        pl.shuffle(shuffle, first=True)
        videoplayer.play(play_queue=pl, resume=resume)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': 'Play Next'})

        if self.mediaItem.type != 'artist':
            if self.mediaItem.isWatched:
                options.append({'key': 'mark_unwatched', 'display': 'Mark Unwatched'})
            else:
                options.append({'key': 'mark_watched', 'display': 'Mark Watched'})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})

        options.append(dropdown.SEPARATOR)

        options.append({'key': 'to_section', 'display': u'Go to {0}'.format(self.mediaItem.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, (880, 618), close_direction='left')
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.mediaItem.markWatched()
            self.updateItems()
            self.updateProperties()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            self.mediaItem.markUnwatched()
            self.updateItems()
            self.updateProperties()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_section':
            self.goHome(self.mediaItem.getLibrarySectionId())

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
            y += 360
        if xbmc.getCondVisibility('Control.IsVisible(502)'):
            y += 520
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 300
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)'):
            y -= 360
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(502)'):
            y -= 500

        focus = int(xbmc.getInfoLabel('Container(403).Position'))

        x = ((focus + 1) * 304) - 100
        return x, y

    def updateItems(self):
        self.fill(update=True)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(
            obj.title or '',
            thumbnailImage=obj.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['item.thumb']),
            data_source=obj
        )
        return mli

    @busy.dialog()
    def fill(self, update=False):
        items = []
        idx = 0
        for season in self.mediaItem.seasons():
            mli = self.createListItem(season)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
                mli.setProperty('unwatched.count', not season.isWatched and str(season.unViewedLeafCount) or '')
                items.append(mli)
                idx += 1

        if update:
            self.subItemListControl.replaceItems(items)
        else:
            self.subItemListControl.reset()
            self.subItemListControl.addItems(items)

    def fillExtras(self):
        items = []
        idx = 0

        if not self.mediaItem.extras:
            self.extraListControl.reset()
            return False

        for extra in self.mediaItem.extras():
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
        if not self.mediaItem.related:
            self.relatedListControl.reset()
            return has_prev

        self.setProperty('divider.{0}'.format(self.RELATED_LIST_ID), has_prev and '1' or '')

        for rel in self.mediaItem.related()[0].items:
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
        if not self.mediaItem.roles:
            self.rolesListControl.reset()
            return has_prev

        self.setProperty('divider.{0}'.format(self.ROLES_LIST_ID), has_prev and '1' or '')

        for role in self.mediaItem.roles():
            mli = kodigui.ManagedListItem(role.tag, role.role, thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM), data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True


class ArtistWindow(ShowWindow):
    xmlFile = 'script-plex-artist.xml'

    SUB_ITEM_LIST_ID = 101

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)

        self.setup()

        self.setFocusId(self.PLAY_BUTTON_ID)

    def setup(self):
        self.updateProperties()
        self.fill()

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.mediaItem.all(), self.mediaItem.getServer(), self.mediaItem)
        pl.startShuffled = shuffle
        w = musicplayer.MusicPlayerWindow.open(track=pl.current(), playlist=pl)
        del w

    def updateProperties(self):
        self.setProperty('summary', self.mediaItem.summary)
        self.setProperty('thumb', self.mediaItem.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['main.thumb']))
        self.setProperty(
            'background',
            self.mediaItem.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )

    @busy.dialog()
    def fill(self):
        self.mediaItem.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
        self.setProperty('artist.title', self.mediaItem.title)
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])
        self.setProperty('artist.genre', genres)
        items = []
        idx = 0
        for album in sorted(self.mediaItem.albums(), key=lambda x: x.year):
            mli = self.createListItem(album)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('year', album.year)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
                items.append(mli)
                idx += 1

        self.subItemListControl.reset()
        self.subItemListControl.addItems(items)
