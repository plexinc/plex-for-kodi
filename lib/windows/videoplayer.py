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
        self.setBackground()
        self.play()

    def onReInit(self):
        self.setBackground()

    def setBackground(self):
        if self.video:
            self.setProperty('background', self.video.defaultArt.asTranscodedImageURL(1920, 1080, blur=128, opacity=60, background=colors.noAlpha.Background))
        else:
            self.setProperty(
                'background',
                self.playQueue.defaultArt.asTranscodedImageURL(1920, 1080, blur=128, opacity=60, background=colors.noAlpha.Background)
            )

    def sessionEnded(self, **kwargs):
        util.DEBUG_LOG('VideoPlayerWindow: Session ended - closing')
        self.doClose()

    def play(self):
        if self.playQueue:
            player.PLAYER.playVideoPlaylist(self.playQueue)
        elif self.video:
            player.PLAYER.playVideo(self.video, resume=self.resume, force_update=True)


def play(video=None, play_queue=None, resume=False):
    w = VideoPlayerWindow.open(video=video, play_queue=play_queue, resume=resume)
    del w
