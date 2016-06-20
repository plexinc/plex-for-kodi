import threading
import xbmc
import xbmcgui
import kodijsonrpc
from windows import seekdialog, playerbackground
import util
from plexnet import plexplayer


class SeekPlayerHandler(object):
    def __init__(self, player):
        self.player = player
        self.dialog = seekdialog.SeekDialog.create(show=False, handler=self)
        self.duration = 0
        self.offset = 0
        self.seeking = False

    def setup(self, duration, offset, bif_url, title='', title2='', seeking=False):
        self.seeking = seeking
        self.duration = duration
        self.dialog.setup(duration, offset, bif_url, title, title2)

    def onSeekAborted(self):
        if self.seeking:
            self.seeking = False
            self.player.control('play')

    def showSeekDialog(self, from_seek=False):
        xbmc.executebuiltin('Dialog.Close(videoosd,true)')
        self.updateOffset()
        self.dialog.show()
        self.dialog.update(self.offset, from_seek)

    def seek(self, offset):
        self.seeking = True
        self.offset = offset
        # self.player.control('play')
        util.DEBUG_LOG('New player offset: {0}'.format(self.offset))
        self.player._playVideo(offset, seeking=True)

    def closeSeekDialog(self):
        if self.dialog:
            self.dialog.doClose()

    def onPlayBackStarted(self):
        self.seeking = False

    def onPlayBackPaused(self):
        pass

    def onPlayBackResumed(self):
        self.closeSeekDialog()

    def onPlayBackStopped(self):
        self.closeSeekDialog()
        if not self.seeking:
            self.player.close()

    def onPlayBackEnded(self):
        self.closeSeekDialog()
        if not self.seeking:
            self.player.close()

    def onPlayBackSeek(self, time, offset):
        self.seeking = True
        self.player.control('pause')
        self.updateOffset()
        self.showSeekDialog(from_seek=True)

    def updateOffset(self):
        self.offset = int(self.player.getTime() * 1000)

    def onPlayBackFailed(self):
        self.seeking = False
        self.player.close()
        return True

    def onVideoWindowOpened(self):
        pass

    def onVideoWindowClosed(self):
        self.closeSeekDialog()
        if not self.seeking:
            self.player.stop()
            self.player.close()

    def onVideoOSD(self):
        # xbmc.executebuiltin('Dialog.Close(seekbar,true)')  # Doesn't work :)
        if not self.seeking:
            self.showSeekDialog()

    def tick(self):
        self.dialog.tick()

    def close(self):
        self.closeSeekDialog()


class PlexPlayer(xbmc.Player):
    def init(self):
        self._closed = False
        self.video = None
        self.xbmcMonitor = xbmc.Monitor()
        self.handler = SeekPlayerHandler(self)
        self.playerBackground = playerbackground.PlayerBackground.create()
        self.seekStepsSetting = util.SettingControl('videoplayer.seeksteps', 'Seek steps', disable_value=[-10, 10])
        self.seekDelaySetting = util.SettingControl('videoplayer.seekdelay', 'Seek delay', disable_value=0)
        return self

    def open(self):
        self._closed = False
        self.monitor()

    def close(self, shutdown=False):
        self.playerBackground.doClose()
        self._closed = True
        if shutdown:
            del self.playerBackground
            self.playerBackground = None

    def reset(self):
        self.started = False
        self.handler = None

    def control(self, cmd):
        if cmd == 'play':
            if xbmc.getCondVisibility('Player.Paused'):
                xbmc.executebuiltin('PlayerControl(Play)')
        elif cmd == 'pause':
            if not xbmc.getCondVisibility('Player.Paused'):
                xbmc.executebuiltin('PlayerControl(Play)')

    def videoIsFullscreen(self):
        return xbmc.getCondVisibility('VideoPlayer.IsFullscreen')

    def playAt(self, path, ms):
        """
        Plays the video specified by path.
        Optionally set the start position with h,m,s,ms keyword args.
        """
        seconds = ms / 1000.0

        h = int(seconds / 3600)
        m = int((seconds % 3600) / 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)

        kodijsonrpc.rpc.Player.Open(
            item={'file': path},
            options={'resume': {'hours': h, 'minutes': m, 'seconds': s, 'milliseconds': ms}}
        )

    def play(self, *args, **kwargs):
        self.started = False
        xbmc.Player.play(self, *args, **kwargs)

    def playVideo(self, video, resume=False):
        self.video = video
        self.open()
        self._playVideo(resume and video.viewOffset.asInt() or 0)

    def _playVideo(self, offset=0, seeking=False):
        pobj = plexplayer.PlexPlayer(self.video, offset)
        url = pobj.build().streamUrls[0]
        bifURL = pobj.getBifUrl()
        util.DEBUG_LOG('Playing URL(+{1}ms): {0}{2}'.format(url, offset, bifURL and ' - indexed' or ''))
        self.handler.setup(self.video.duration.asInt(), offset, bifURL, title=self.video.grandparentTitle, title2=self.video.title, seeking=seeking)
        self.play(url + '&X-Plex-Platform=Chrome')

    def onPlayBackStarted(self):
        self.started = True
        util.DEBUG_LOG('Player - STARTED')
        if not self.handler:
            return
        self.handler.onPlayBackStarted()

    def onPlayBackPaused(self):
        util.DEBUG_LOG('Player - PAUSED')
        if not self.handler:
            return
        self.handler.onPlayBackPaused()

    def onPlayBackResumed(self):
        util.DEBUG_LOG('Player - RESUMED')
        if not self.handler:
            return
        self.handler.onPlayBackResumed()

    def onPlayBackStopped(self):
        if not self.started:
            self.onPlayBackFailed()

        util.DEBUG_LOG('Player - STOPPED' + (not self.started and ': FAILED' or ''))
        if not self.handler:
            return
        self.handler.onPlayBackStopped()

    def onPlayBackEnded(self):
        if not self.started:
            self.onPlayBackFailed()

        util.DEBUG_LOG('Player - ENDED' + (not self.started and ': FAILED' or ''))
        if not self.handler:
            return
        self.handler.onPlayBackEnded()

    def onPlayBackSeek(self, time, offset):
        util.DEBUG_LOG('Player - SEEK')
        if not self.handler:
            return
        self.handler.onPlayBackSeek(time, offset)

    def onPlayBackFailed(self):
        if not self.handler:
            return

        if self.handler.onPlayBackFailed():
            xbmcgui.Dialog.ok('Failed', 'Playback failed')

    def onVideoWindowOpened(self):
        util.DEBUG_LOG('Player: Video window opened')
        try:
            self.handler.onVideoWindowOpened()
        except:
            util.ERROR()

    def onVideoWindowClosed(self):
        util.DEBUG_LOG('Player: Video window closed')
        try:
            self.handler.onVideoWindowClosed()
            # self.stop()
        except:
            util.ERROR()

    def onVideoOSD(self):
        util.DEBUG_LOG('Player: Video OSD opened')
        try:
            self.handler.onVideoOSD()
        except:
            util.ERROR()

    def stopAndWait(self):
        if self.isPlayingVideo():
            util.DEBUG_LOG('Player (Recording): Stopping for external wait')
            self.stop()
            self.handler.waitForStop()

    def monitor(self):
        threading.Thread(target=self._monitor, name='PLAYER:MONITOR').start()

    def _monitor(self):
        with self.playerBackground.asContext():
            with self.seekDelaySetting.suspend():
                with self.seekStepsSetting.suspend():
                    while not xbmc.abortRequested and not self._closed:
                        # Monitor loop
                        if self.isPlayingVideo():
                            util.DEBUG_LOG('Player: Monitoring')

                        hasFullScreened = False

                        ct = 0
                        while self.isPlayingVideo() and not xbmc.abortRequested and not self._closed:
                            self.xbmcMonitor.waitForAbort(0.1)
                            if xbmc.getCondVisibility('Window.IsActive(videoosd)'):
                                self.onVideoOSD()

                            if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
                                if not hasFullScreened:
                                    hasFullScreened = True
                                    self.onVideoWindowOpened()
                            elif hasFullScreened and not xbmc.getCondVisibility('Window.IsVisible(busydialog)'):
                                hasFullScreened = False
                                self.onVideoWindowClosed()

                            ct += 1
                            if ct > 9:
                                ct = 0
                                self.handler.tick()

                        if hasFullScreened:
                            self.onVideoWindowClosed()

                        # Idle loop
                        if not self.isPlayingVideo():
                            util.DEBUG_LOG('Player: Idling...')

                        while not self.isPlayingVideo() and not xbmc.abortRequested and not self._closed:
                            self.xbmcMonitor.waitForAbort(0.1)

        self.handler.close()
        self.close()
        util.DEBUG_LOG('Player: Closed')

PLAYER = PlexPlayer().init()
