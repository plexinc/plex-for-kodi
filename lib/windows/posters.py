import random
import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util
from lib import player
from lib import backgroundthread

import busy
import subitems
import preplay
import photos
import plexnet
import musicplayer

KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

MOVE_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_MOVE_UP,
        xbmcgui.ACTION_MOVE_DOWN,
        xbmcgui.ACTION_MOUSE_MOVE,
        xbmcgui.ACTION_PAGE_UP,
        xbmcgui.ACTION_PAGE_DOWN
    )
)

THUMB_POSTER_DIM = (287, 425)
THUMB_AR16X9_DIM = (619, 348)
THUMB_SQUARE_DIM = (425, 425)

TYPE_KEYS = {
    'episode': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM,
    },
    'season': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM
    },
    'movie': {
        'fallback': 'movie',
        'thumb_dim': THUMB_POSTER_DIM
    },
    'show': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM
    },
    'album': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'artist': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'track': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'photo': {
        'fallback': 'photo',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'clip': {
        'fallback': 'movie16x9',
        'thumb_dim': THUMB_AR16X9_DIM
    },
}


class ChunkRequestTask(backgroundthread.Task):
    def setup(self, section, start, size, callback):
        self.section = section
        self.start = start
        self.size = size
        self.callback = callback
        return self

    def contains(self, pos):
        return self.start <= pos <= (self.start + self.size)

    def run(self):
        if self.isCanceled():
            return

        try:
            items = self.section.all(self.start, self.size)
            if self.isCanceled():
                return
            self.callback(items, self.start)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on section: {0}'.format(repr(self.section.title)))


class PostersWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-posters.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    POSTERS_PANEL_ID = 101
    KEY_LIST_ID = 151

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    MORE_BUTTON_ID = 303
    VIEWTYPE_BUTTON_ID = 304

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.section = kwargs.get('section')
        self.keyItems = {}
        self.firstOfKeyItems = {}
        self.tasks = []
        self.backgroundSet = False
        self.exitCommand = None

    def doClose(self):
        for task in self.tasks:
            task.cancel()
        kodigui.BaseWindow.doClose(self)

    def onFirstInit(self):
        self.showPanelControl = kodigui.ManagedControlList(self, self.POSTERS_PANEL_ID, 5)
        self.keyListControl = kodigui.ManagedControlList(self, self.KEY_LIST_ID, 27)

        self.setTitle()
        if self.section.TYPE in ('photo', 'photodirectory'):
            self.fillPhotos()
        else:
            self.fillShows()
        self.setFocusId(self.POSTERS_PANEL_ID)

    def onAction(self, action):
        try:
            if action.getId() in MOVE_SET:
                controlID = self.getFocusId()
                if controlID == self.POSTERS_PANEL_ID:
                    self.updateKey()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return

            self.updateItem()

        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.doClose()
        elif controlID == self.POSTERS_PANEL_ID:
            self.showPanelClicked()
        elif controlID == self.KEY_LIST_ID:
            self.keyClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()

    def onFocus(self, controlID):
        if controlID == self.KEY_LIST_ID:
            self.selectKey()

    def updateKey(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        self.setProperty('key', mli.getProperty('key'))

    def selectKey(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        li = self.keyItems.get(mli.getProperty('key'))
        if not li:
            return
        self.keyListControl.selectItem(li.pos())

    def keyClicked(self):
        li = self.keyListControl.getSelectedItem()
        if not li:
            return

        mli = self.firstOfKeyItems.get(li.dataSource)
        if not mli:
            return

        self.showPanelControl.selectItem(mli.pos())
        self.setFocusId(self.POSTERS_PANEL_ID)
        self.setProperty('key', li.dataSource)

    def playButtonClicked(self, shuffle=False):
        items = [i.dataSource for i in self.showPanelControl]

        if self.section.TYPE in ('movie', 'show'):
            if self.section.TYPE == 'movie':
                pl = plexnet.plexobjects.TempPlaylist(items, self.section.getServer())
            elif self.section.TYPE == 'show':
                pl = plexnet.plexobjects.TempLeafedPlaylist(items, self.section.getServer())
            else:
                return

            pl.shuffle(shuffle, first=True)
            player.PLAYER.playVideoPlaylist(playlist=pl)
        elif self.section.TYPE == 'artist':
            # pl = plexnet.plexobjects.TempLeafedPlaylist(items, self.section.getServer())
            # pl.startShuffled = shuffle
            # musicplayer.MusicPlayerWindow.open(track=pl.current(), playlist=pl)
            pass

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def showPanelClicked(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return

        if self.section.TYPE == 'show':
            self.showSeasons(mli.dataSource)
        elif self.section.TYPE == 'movie':
            self.showPreplay(mli.dataSource)
        elif self.section.TYPE == 'artist':
            self.showArtist(mli.dataSource)
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.showPhoto(mli.dataSource)

    def showSeasons(self, show):
        w = subitems.ShowWindow.open(media_item=show)
        self.onChildWindowClosed(w)

    def showPreplay(self, movie):
        w = preplay.PrePlayWindow.open(video=movie)
        self.onChildWindowClosed(w)

    def showArtist(self, artist):
        w = subitems.ArtistWindow.open(media_item=artist)
        self.onChildWindowClosed(w)

    def showPhoto(self, photo):
        if isinstance(photo, plexnet.photo.Photo):
            w = photos.PhotoWindow.open(photo=photo)
        elif photo.TYPE == 'clip':
            player.PLAYER.playVideo(photo)
        else:
            w = SquaresWindow.open(section=photo)
            self.onChildWindowClosed(w)

    def onChildWindowClosed(self, w):
        try:
            if w.exitCommand == 'HOME':
                self.exitCommand = 'HOME'
                self.doClose()
        finally:
            del w

    def setTitle(self):
        if self.section.TYPE == 'artist':
            self.setProperty('screen.title', 'MUSIC')
        elif self.section.TYPE == 'photo':
            self.setProperty('screen.title', 'PHOTOS')
        else:
            self.setProperty('screen.title', self.section.TYPE == 'show' and 'TV SHOWS' or 'MOVIES')

    def updateItem(self, mli=None):
        mli = mli or self.showPanelControl.getSelectedItem()
        if not mli or mli.dataSource:
            return

        for task in self.tasks:
            if task.contains(mli.pos()):
                util.DEBUG_LOG('Moving task to front: {0}'.format(task))
                backgroundthread.BGThreader.moveToFront(task)
                break

    def setBackground(self, items):
        if self.backgroundSet:
            return
        self.backgroundSet = True

        item = random.choice(items)
        self.setProperty('background', item.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))

    @busy.dialog()
    def fillShows(self):
        items = []
        jitems = []
        self.keyItems = {}
        self.firstOfKeyItems = {}
        totalSize = 0

        jumpList = self.section.jumpList()
        idx = 0
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

        for ji in jumpList:
            mli = kodigui.ManagedListItem(ji.title, data_source=ji.key)
            mli.setProperty('key', ji.key)
            self.keyItems[ji.key] = mli
            jitems.append(mli)
            totalSize += ji.size.asInt()

            for x in range(ji.size.asInt()):
                mli = kodigui.ManagedListItem('')
                mli.setProperty('key', ji.key)
                mli.setProperty('thumb.fallback', fallback)
                mli.setProperty('index', str(idx))
                items.append(mli)
                if not x:  # i.e. first item
                    self.firstOfKeyItems[ji.key] = mli
                idx += 1

        self.showPanelControl.addItems(items)
        self.keyListControl.addItems(jitems)

        if jumpList:
            self.setProperty('key', jumpList[0].key)

        tasks = []
        for start in range(0, totalSize, 500):
            tasks.append(ChunkRequestTask().setup(self.section, start, 500, self.chunkCallback))

        self.tasks = tasks
        backgroundthread.BGThreader.addTasksToFront(tasks)

    @busy.dialog()
    def fillPhotos(self):
        items = []
        keys = []
        self.firstOfKeyItems = {}
        idx = 0

        photos = self.section.all()
        if not photos:
            return

        photo = random.choice(photos)
        self.setProperty('background', photo.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))
        thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

        for photo in photos:
            title = photo.title
            mli = kodigui.ManagedListItem(title, thumbnailImage=photo.defaultThumb.asTranscodedImageURL(*thumbDim), data_source=photo)
            mli.setProperty('thumb.fallback', fallback)
            mli.setProperty('index', str(idx))

            key = title[0].upper()
            if key not in KEYS:
                key = '#'
            if key not in keys:
                self.firstOfKeyItems[key] = mli
                keys.append(key)
            mli.setProperty('key', str(key))
            items.append(mli)
            idx += 1

        litems = []
        self.keyItems = {}
        for key in keys:
            mli = kodigui.ManagedListItem(key, data_source=key)
            mli.setProperty('key', key)
            self.keyItems[key] = mli
            litems.append(mli)

        self.showPanelControl.addItems(items)
        self.keyListControl.addItems(litems)

        if keys:
            self.setProperty('key', keys[0])

    def chunkCallback(self, items, start):
        pos = start
        self.setBackground(items)
        thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
        for obj in items:
            mli = self.showPanelControl[pos]
            mli.setLabel(obj.defaultTitle or '')
            mli.setThumbnailImage(obj.defaultThumb.asTranscodedImageURL(*thumbDim))
            mli.dataSource = obj
            pos += 1

    def showAudioPlayer(self):
        import musicplayer
        w = musicplayer.MusicPlayerWindow.open()
        del w


class SquaresWindow(PostersWindow):
    xmlFile = 'script-plex-squares.xml'
