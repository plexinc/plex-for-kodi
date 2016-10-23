import time
import threading

import xbmc
import xbmcgui
import kodigui

import busy
import opener
import search
import dropdown
import windowutils

from lib import player
from lib import colors
from lib import util


class PostPlayWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-post_play.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    NEXT_DIM = (537, 303)
    PREV_DIM = (462, 259)
    ONDECK_DIM = (329, 185)
    RELATED_DIM = (268, 397)
    ROLES_DIM = (268, 268)

    OPTIONS_GROUP_ID = 200

    PREV_BUTTON_ID = 101
    NEXT_BUTTON_ID = 102

    ONDECK_LIST_ID = 400
    RELATED_LIST_ID = 401
    ROLES_LIST_ID = 403

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.playlist = kwargs.get('playlist')
        self.handler = kwargs.get('handler')
        self.video = self.playlist.current()
        self.prev = self.playlist.prevItem()
        self.show_ = self.video.show()
        self.videos = None
        self.exitCommand = None
        self.trailer = None
        self.aborted = True
        self.timeout = None

    def doClose(self):
        self.timeout = None
        kodigui.ControlledWindow.doClose(self)

    def onFirstInit(self):
        self.onDeckListControl = kodigui.ManagedControlList(self, self.ONDECK_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)

        self.setup()

    def onReInit(self):
        # self.video.reload()
        # self.setInfo()
        pass

    def onAction(self, action):
        try:
            self.cancelTimer()
            if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
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
        elif controlID == self.ONDECK_LIST_ID:
            self.openItem(self.onDeckListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()
        elif controlID == self.PREV_BUTTON_ID:
            self.playVideo(prev=True)
        elif controlID == self.NEXT_BUTTON_ID:
            self.playVideo()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.show_AudioPlayer()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def onFocus(self, controlID):
        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))
        else:
            self.setProperty('hub.focus', '')

        if xbmc.getCondVisibility('Control.HasFocus(101) | Control.HasFocus(102) | ControlGroup(200).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(60).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.video.getLibrarySectionId() or None))

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
        y = 1000
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

    def playVideo(self, prev=False):
        try:
            if prev:
                self.playlist.prev()
            self.aborted = False
            player.PLAYER.playVideoPlaylist(self.playlist, handler=self.handler)
        finally:
            self.doClose()

    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item))

    @busy.dialog()
    def setup(self):
        self.setProperty(
            'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(self.video.type in ('show', 'season', 'episode') and 'show' or 'movie')
        )

        util.DEBUG_LOG('PostPlay: Showing video info: {0}'.format(self.video))
        self.show_.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
        self.setInfo()
        self.fillOnDeck()
        hasPrev = self.fillRelated()
        self.fillRoles(hasPrev)
        self.startTimer()

    def startTimer(self):
        util.DEBUG_LOG('Staring post-play timer')
        self.timeout = time.time() + 16
        threading.Thread(target=self.countdown).start()

    def cancelTimer(self):
        util.DEBUG_LOG('Canceling post-play timer')
        self.timeout = None
        self.setProperty('countdown', '')

    def countdown(self):
        while self.timeout and not util.MONITOR.waitForAbort(0.1):
            now = time.time()
            if self.timeout and now > self.timeout:
                util.DEBUG_LOG('Post-play timer finished')
                self.timeout = None
                self.playVideo()
                break
            else:
                self.setProperty('countdown', str(min(15, int((self.timeout or now) - now))))

    def setInfo(self):
        self.setProperty('background', self.video.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background))
        self.setProperty('info.title', self.video.title)
        self.setProperty('info.duration', util.durationToText(self.video.duration.asInt()))
        self.setProperty('info.summary', self.video.summary)

        self.setProperty('next.thumb', self.video.thumb.asTranscodedImageURL(*self.NEXT_DIM))
        if self.prev:
            self.setProperty('prev.thumb', self.prev.thumb.asTranscodedImageURL(*self.PREV_DIM))

        if self.video.type == 'episode':
            self.setProperty('related.header', 'Related Shows')
            self.setProperty('info.date', util.cleanLeadingZeros(self.video.originallyAvailableAt.asDatetime('%B %d, %Y')))

            self.setProperty('next.title', self.video.grandparentTitle)
            self.setProperty('next.subtitle', u'Season {0} \u2022 Episode {1}'.format(self.video.parentIndex, self.video.index))
            if self.prev:
                self.setProperty('prev.title', self.prev.grandparentTitle)
                self.setProperty('prev.subtitle', u'Season {0} \u2022 Episode {1}'.format(self.prev.parentIndex, self.prev.index))
        elif self.video.type == 'movie':
            self.setProperty('related.header', 'Related Movies')
            self.setProperty('info.date', self.video.year)

            self.setProperty('next.title', self.video.title)
            self.setProperty('next.subtitle', self.video.year)
            if self.prev:
                self.setProperty('prev.title', self.prev.title)
                self.setProperty('prev.subtitle', self.prev.year)

    def fillOnDeck(self):
        items = []
        idx = 0

        onDecks = self.show_.sectionOnDeck()
        if not onDecks:
            self.onDeckListControl.reset()
            return False

        for ondeck in onDecks:
            title = ondeck.grandparentTitle or ondeck.title
            mli = kodigui.ManagedListItem(title or '', thumbnailImage=ondeck.thumb.asTranscodedImageURL(*self.ONDECK_DIM), data_source=ondeck)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty(
                    'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(ondeck.type in ('show', 'season', 'episode') and 'show' or 'movie')
                )
                if ondeck.type in 'episode':
                    mli.setLabel2(u'S{0} \u2022 E{1}'.format(ondeck.parentIndex, ondeck.index))
                else:
                    mli.setLabel2(ondeck.year)

                items.append(mli)
                idx += 1

        if not items:
            return False

        self.onDeckListControl.reset()
        self.onDeckListControl.addItems(items)
        return True

    def fillRelated(self, has_prev=False):
        items = []
        idx = 0

        if not self.show_.related:
            self.relatedListControl.reset()
            return False

        for rel in self.show_.related()[0].items:
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


def show(**kwargs):
    w = PostPlayWindow.open(**kwargs)
    aborted = w.aborted
    del w
    util.garbageCollect()
    return not aborted
