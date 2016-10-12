import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util

from plexnet import playlist

import busy
import episodes
import opener
import info
import musicplayer
import videoplayer
import dropdown
import windowutils


class ShowWindow(kodigui.BaseWindow, windowutils.UtilMixin):
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

    RELATED_DIM = (268, 397)
    ROLES_DIM = (268, 268)

    SUB_ITEM_LIST_ID = 400

    RELATED_LIST_ID = 401
    ROLES_LIST_ID = 403

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    PLAYER_STATUS_BUTTON_ID = 204

    PROGRESS_IMAGE_ID = 250

    INFO_BUTTON_ID = 301
    PLAY_BUTTON_ID = 302
    SHUFFLE_BUTTON_ID = 303
    OPTIONS_BUTTON_ID = 304

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.mediaItem = kwargs.get('media_item')
        self.exitCommand = None

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)

        self.mediaItem.reload(includeRelated=1, includeRelatedCount=10)

        self.updateProperties()
        self.fill()
        hasPrev = self.fillRelated(False)
        self.fillRoles(hasPrev)

        self.setFocusId(self.PLAY_BUTTON_ID)

    def updateProperties(self):
        self.setProperty('title', self.mediaItem.title)
        self.setProperty('summary', self.mediaItem.summary)
        self.setProperty('thumb', self.mediaItem.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['main.thumb']))
        self.setProperty(
            'background',
            self.mediaItem.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('duration', util.durationToText(self.mediaItem.duration.asInt()))
        self.setProperty('info', '')
        self.setProperty('date', self.mediaItem.year)

        self.setProperty('related.header', 'Related Shows')

        if self.mediaItem.creator:
            self.setProperty('directors', u'CREATOR    {0}'.format(self.mediaItem.creator))
        elif self.mediaItem.studio:
            self.setProperty('directors', u'STUDIO    {0}'.format(self.mediaItem.studio))

        cast = u' / '.join([r.tag for r in self.mediaItem.roles()][:5])
        castLabel = 'CAST'
        self.setProperty('writers', cast and u'{0}    {1}'.format(castLabel, cast) or '')

        genres = self.mediaItem.genres()
        self.setProperty('info', genres and (u' / '.join([g.tag for g in genres][:3])) or '')

        if self.mediaItem.userRating:
            stars = str(int(round((self.mediaItem.userRating.asFloat() / 10) * 5)))
            self.setProperty('user.stars', stars)
        elif self.mediaItem.rating:
            stars = str(int(round((self.mediaItem.rating.asFloat() / 10) * 5)))
            self.setProperty('rating.stars', stars)

        if self.mediaItem.ratingImage:
            self.setProperty('rating', self.mediaItem.rating)
            self.setProperty('rating.image', 'script.plex/ratings/{0}.png'.format(self.mediaItem.ratingImage.replace('://', '/')))
            if self.mediaItem.audienceRatingImage:
                self.setProperty('rating2', self.mediaItem.audienceRating)
                self.setProperty('rating2.image', 'script.plex/ratings/{0}.png'.format(self.mediaItem.audienceRatingImage.replace('://', '/')))

        sas = self.mediaItem.selectedAudioStream()
        self.setProperty('audio', sas and sas.getTitle() or 'None')

        sss = self.mediaItem.selectedSubtitleStream()
        self.setProperty('subtitles', sss and sss.getTitle() or 'None')

        width = (int((self.mediaItem.viewedLeafCount.asInt() / self.mediaItem.leafCount.asFloat()) * self.width)) or 1
        self.progressImageControl.setWidth(width)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return

        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.closeWithCommand('HOME')
        elif controlID == self.SUB_ITEM_LIST_ID:
            self.subItemListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.RELATED_LIST_ID:
            self.relatedClicked()
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

    def onFocus(self, controlID):
        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def relatedClicked(self):
        mli = self.relatedListControl.getSelectedItem()
        if not mli:
            return

        self.processCommand(opener.open(mli.dataSource))

    def subItemListClicked(self):
        mli = self.subItemListControl.getSelectedItem()
        if not mli:
            return

        update = False

        if self.mediaItem.type == 'show':
            w = episodes.EpisodesWindow.open(season=mli.dataSource, show=self.mediaItem)
            update = True
        elif self.mediaItem.type == 'artist':
            w = episodes.AlbumWindow.open(season=mli.dataSource, show=self.mediaItem)

        if not mli.dataSource.exists():
            self.subItemListControl.removeItem(mli.pos())

        if not self.subItemListControl.size():
            self.closeWithCommand(w.exitCommand)
            return

        if update:
            mli.setProperty('unwatched.count', not mli.dataSource.isWatched and str(mli.dataSource.unViewedLeafCount) or '')
            self.mediaItem.reload()
            self.updateProperties()

        try:
            self.processCommand(w.exitCommand)
        finally:
            del w

    def infoButtonClicked(self):
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(self.mediaItem.type == 'show' and 'show' or 'music')
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])
        info.InfoWindow.open(
            title=self.mediaItem.title,
            sub_title=genres,
            thumb=self.mediaItem.defaultThumb,
            thumb_fallback=fallback,
            info=self.mediaItem.summary,
            background=self.getProperty('background'),
            is_square=bool(isinstance(self, ArtistWindow))
        )

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.mediaItem.all(), self.mediaItem.getServer())
        pl.shuffle(shuffle, first=True)
        videoplayer.play(play_queue=pl)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': 'Play Next'})

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
            self.closeWithCommand('HOME:{0}'.format(self.mediaItem.getLibrarySectionId()))

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

    def fillRelated(self, has_prev=False):
        items = []
        idx = 0
        if not self.mediaItem.related:
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

        self.relatedListControl.addItems(items)
        return True

    def fillRoles(self, has_prev=False):
        items = []
        idx = 0
        if not self.mediaItem.roles:
            return has_prev

        self.setProperty('divider.{0}'.format(self.ROLES_LIST_ID), has_prev and '1' or '')

        for role in self.mediaItem.roles():
            mli = kodigui.ManagedListItem(role.tag, role.role, thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM), data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        self.rolesListControl.addItems(items)
        return True


class ArtistWindow(ShowWindow):
    xmlFile = 'script-plex-artist.xml'

    SUB_ITEM_LIST_ID = 101

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)

        self.setProperties()
        self.fill()

        self.setFocusId(self.SUB_ITEM_LIST_ID)

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.mediaItem.all(), self.mediaItem.getServer(), self.mediaItem)
        pl.startShuffled = shuffle
        musicplayer.MusicPlayerWindow.open(track=pl.current(), playlist=pl)

    def setProperties(self):
        self.setProperty('summary', self.mediaItem.summary)
        self.setProperty('thumb', self.mediaItem.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['main.thumb']))
        self.setProperty(
            'background',
            self.mediaItem.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )

    @busy.dialog()
    def fill(self):
        self.mediaItem.reload()
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

        self.subItemListControl.addItems(items)
