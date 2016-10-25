import kodigui
from lib import util
from lib import player
from lib import colors


class VideoPlayerWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-video_player.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.playQueue = kwargs.get('play_queue')
        self.video = kwargs.get('video')
        self.resume = bool(kwargs.get('resume'))

    def onFirstInit(self):
        player.PLAYER.on('session.ended', self.sessionEnded)
        player.PLAYER.on('change.background', self.changeBackground)
        self.setBackground()
        self.play()

    def onReInit(self):
        self.setBackground()

    def setBackground(self):
        video = self.video if self.video else self.playQueue.current()
        self.setProperty('background', video.defaultArt.asTranscodedImageURL(1920, 1080, opacity=60, background=colors.noAlpha.Background))

    def changeBackground(self, url, **kwargs):
        self.setProperty('background', url)

    def sessionEnded(self, session_id=None, **kwargs):
        if session_id != id(self):
            util.DEBUG_LOG('VideoPlayerWindow: Ignoring session end (ID: {0} - SessionID: {1})'.format(id(self), session_id))
            return

        util.DEBUG_LOG('VideoPlayerWindow: Session ended - closing (ID: {0})'.format(id(self)))
        self.doClose()

    def play(self):
        util.DEBUG_LOG('VideoPlayerWindow: Starting session (ID: {0})'.format(id(self)))
        if self.playQueue:
            player.PLAYER.playVideoPlaylist(self.playQueue, resume=self.resume, session_id=id(self))
        elif self.video:
            player.PLAYER.playVideo(self.video, resume=self.resume, force_update=True, session_id=id(self))


def play(video=None, play_queue=None, resume=False):
    w = VideoPlayerWindow.open(video=video, play_queue=play_queue, resume=resume)
    player.PLAYER.off('session.ended', w.sessionEnded)
    player.PLAYER.off('change.background', w.changeBackground)
    del w
    util.garbageCollect()
