import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util

from plexnet import playlist

import busy
import preplay
import musicplayer
import videoplayer
import dropdown


class EpisodesWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-episodes.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_AR16X9_DIM = (178, 100)
    POSTER_DIM = (420, 630)

    EPISODE_PANEL_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.season = kwargs.get('season')
        self.show = kwargs.get('show')
        self.exitCommand = None
        self.lastFocusID = None
        self.mode = False

    def onFirstInit(self):
        self.episodePanelControl = kodigui.ManagedControlList(self, self.EPISODE_PANEL_ID, 5)

        self.setProperties()
        self.fillEpisodes()
        self.setFocusId(self.EPISODE_PANEL_ID)
        self.checkForHeaderFocus(xbmcgui.ACTION_MOVE_DOWN)

    def onReInit(self):
        self.setMode()

    def onAction(self, action):
        controlID = self.getFocusId()
        try:
            if controlID == self.EPISODE_PANEL_ID:
                self.checkForHeaderFocus(action)
                if self.checkOptionsAction(action):
                    return

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

    def checkOptionsAction(self, action):
        if action == xbmcgui.ACTION_MOVE_RIGHT:
            if self.lastFocusID == self.EPISODE_PANEL_ID and not self.mode == 'ignore':
                if not self.mode:
                    self.setMode('options')
                    return True
                else:
                    self.setFocusId(152)
                    return False
            else:
                self.setMode()

        elif action == xbmcgui.ACTION_MOVE_LEFT:
            if self.lastFocusID == self.EPISODE_PANEL_ID and not self.mode == 'ignore':
                if not self.mode:
                    self.setFocusId(300)
                    return False
                else:
                    self.setMode()
                    return True
            else:
                self.setMode()

        return False

    def setMode(self, mode=None):
        self.mode = mode
        self.setProperty('mode.options', self.mode == 'options' and '1' or '')

    def onFocus(self, controlID):
        self.lastFocusID = controlID
        if controlID == self.EPISODE_PANEL_ID:
            if self.mode == False:
                self.setMode()
            else:
                self.setMode('ignore')

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.exitCommand = 'HOME'
            self.doClose()
        elif controlID == self.EPISODE_PANEL_ID:
            self.episodePanelClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.season.all(), self.season.getServer())
        pl.shuffle(shuffle, first=True)
        videoplayer.play(play_queue=pl)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def episodePanelClicked(self):
        mli = self.episodePanelControl.getSelectedItem()
        if not mli:
            return

        if self.mode == 'options':
            self.optionsButtonClicked(mli)
        else:
            w = preplay.PrePlayWindow.open(video=mli.dataSource)
            mli.setProperty('watched', mli.dataSource.isWatched and '1' or '')
            self.season.reload()
            try:
                if w.exitCommand == 'HOME':
                    self.exitCommand = 'HOME'
                    self.doClose()
            finally:
                del w

    def optionsButtonClicked(self, item=None):
        options = []

        if item:
            if item.dataSource.isWatched:
                options.append(('mark_unwatched', 'Mark Unwatched'))
            else:
                options.append(('mark_watched', 'Mark Watched'))
        else:
            if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
                options.append(('play_next', 'Play Next'))

            if not isinstance(self, AlbumWindow):
                if self.season.isWatched:
                    options.append(('mark_unwatched', 'Mark Unwatched'))
                else:
                    options.append(('mark_watched', 'Mark Watched'))

            # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
            #     options.append(('add_to_queue', 'Add To Queue'))

            # if False:
            #     options.append(('add_to_playlist', 'Add To Playlist'))

        pos = (460, 1106)
        bottom=True
        setDropdownProp = False
        if item:
            pos = (1490, 167 + (self.episodePanelControl.getViewPosition() * 100))
            bottom=False
            setDropdownProp = True
        choice = dropdown.showDropdown(options, pos, pos_is_bottom=bottom, close_direction='right', set_dropdown_prop=setDropdownProp)
        if not choice:
            return

        if choice == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice == 'mark_watched':
            media = item and item.dataSource or self.season
            media.markWatched()
            self.updateItems(item)
        elif choice == 'mark_unwatched':
            media = item and item.dataSource or self.season
            media.markUnwatched()
            self.updateItems(item)

    def checkForHeaderFocus(self, action):
        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if self.episodePanelControl.getSelectedItem().getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            if self.episodePanelControl.getSelectedItem().getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

    def setProperties(self):
        self.setProperty(
            'background',
            (self.show or self.season.show()).art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('season.thumb', self.season.thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('show.title', self.show and self.show.title or '')
        self.setProperty('season.title', self.season.title)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(
            obj.title, obj.originallyAvailableAt.asDatetime('%b %d, %Y'), thumbnailImage=obj.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM), data_source=obj
        )
        mli.setProperty('episode.number', str(obj.index) or '')
        mli.setProperty('episode.duration', util.durationToText(obj.duration.asInt()))
        mli.setProperty('watched', obj.isWatched and '1' or '')
        return mli

    def updateItems(self, item=None):
        if item:
            self.season.reload()
            item.setProperty('watched', item.dataSource.isWatched and '1' or '')
        else:
            self.fillEpisodes(update=True)

    @busy.dialog()
    def fillEpisodes(self, update=False):
        items = []
        idx = 0
        for episode in self.season.episodes():
            mli = self.createListItem(episode)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        if update:
            self.episodePanelControl.replaceItems(items)
        else:
            self.episodePanelControl.reset()
            self.episodePanelControl.addItems(items)

    def showAudioPlayer(self):
        import musicplayer
        w = musicplayer.MusicPlayerWindow.open()
        del w


class AlbumWindow(EpisodesWindow):
    xmlFile = 'script-plex-album.xml'

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.season.all(), self.season.getServer())
        pl.startShuffled = shuffle
        musicplayer.MusicPlayerWindow.open(track=pl.current(), playlist=pl)

    def episodePanelClicked(self):
        mli = self.episodePanelControl.getSelectedItem()
        if not mli:
            return

        w = musicplayer.MusicPlayerWindow.open(track=mli.dataSource, album=self.season)
        del w

    def setProperties(self):
        self.setProperty(
            'background',
            self.season.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('season.thumb', self.season.thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('artist.title', self.season.parentTitle or '')
        self.setProperty('album.title', self.season.title)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(
            obj.title, thumbnailImage=obj.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM), data_source=obj
        )
        mli.setProperty('track.number', str(obj.index) or '')
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(obj.duration.asInt()))
        return mli

    @busy.dialog()
    def fillEpisodes(self):
        items = []
        idx = 0
        multiDisc = 0

        for track in self.season.tracks():
            disc = track.parentIndex.asInt()
            if disc > 1:
                if not multiDisc:
                    items.insert(0, kodigui.ManagedListItem('DISC 1', properties={'is.header': '1'}))

                if disc != multiDisc:
                    items[-1].setProperty('is.footer', '1')
                    multiDisc = disc
                    items.append(kodigui.ManagedListItem('DISC {0}'.format(disc), properties={'is.header': '1'}))

            mli = self.createListItem(track)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('artist', self.season.parentTitle)
                mli.setProperty('disc', str(disc))
                mli.setProperty('album', self.season.title)
                mli.setProperty('number', '{0:0>2}'.format(track.index))
                items.append(mli)
                idx += 1

        if items:
            items[-1].setProperty('is.footer', '1')

        self.episodePanelControl.addItems(items)
