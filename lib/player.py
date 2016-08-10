import base64
import threading
import xbmc
import xbmcgui
import kodijsonrpc
import colors
from windows import seekdialog, playerbackground
import util
from plexnet import plexplayer


class BasePlayerHandler(object):
    def __init__(self, player):
        self.player = player

    def onPlayBackStarted(self):
        pass

    def onPlayBackPaused(self):
        pass

    def onPlayBackResumed(self):
        pass

    def onPlayBackStopped(self):
        pass

    def onPlayBackEnded(self):
        pass

    def onPlayBackSeek(self, time, offset):
        pass

    def onPlayBackFailed(self):
        pass

    def onVideoWindowOpened(self):
        pass

    def onVideoWindowClosed(self):
        pass

    def onVideoOSD(self):
        pass

    def onSeekOSD(self):
        pass

    def tick(self):
        pass

    def close(self):
        pass


class SeekPlayerHandler(BasePlayerHandler):
    NO_SEEK = 0
    SEEK_INIT = 1
    SEEK_IN_PROGRESS = 2
    SEEK_PLAYLIST = 3

    MODE_ABSOLUTE = 0
    MODE_RELATIVE = 1

    def __init__(self, player):
        self.player = player
        self.dialog = seekdialog.SeekDialog.create(show=False, handler=self)
        self.playlist = None
        self.playlistPos = 0
        self.reset()

    def reset(self):
        self.duration = 0
        self.offset = 0
        self.seeking = self.NO_SEEK
        self.seekOnStart = 0
        self.mode = self.MODE_RELATIVE

    def setup(self, duration, offset, bif_url, title='', title2='', seeking=NO_SEEK):
        self.seeking = seeking
        self.duration = duration
        self.dialog.setup(duration, offset, bif_url, title, title2)

    def next(self):
        if not self.playlist:
            return False

        self.playlistPos += 1
        if self.playlistPos >= len(self.playlist.items()):
            self.playlistPos = len(self.playlist.items()) - 1
            return False

        self.seeking = self.SEEK_PLAYLIST
        self.player.playVideoPlaylist(self.playlist, self.playlistPos, handler=self)

        return True

    def prev(self):
        if not self.playlist:
            return False

        self.playlistPos -= 1
        if self.playlistPos < 0:
            self.playlistPos = 0
            return False

        self.seeking = self.SEEK_PLAYLIST
        self.player.playVideoPlaylist(self.playlist, self.playlistPos, handler=self)

        return True

    def onSeekAborted(self):
        if self.seeking:
            self.seeking = self.NO_SEEK
            self.player.control('play')

    def showSeekDialog(self, from_seek=False):
        xbmc.executebuiltin('Dialog.Close(videoosd,true)')
        if xbmc.getCondVisibility('Player.showinfo'):
            xbmc.executebuiltin('Action(Info)')
        self.updateOffset()
        self.dialog.show()
        self.dialog.update(self.offset, from_seek)

    def seek(self, offset):
        if self.mode == self.MODE_ABSOLUTE:
            self.offset = offset
            util.DEBUG_LOG('New player offset: {0}'.format(self.offset))
            return self.seekAbsolute(offset)

        self.seeking = self.SEEK_IN_PROGRESS
        self.offset = offset
        # self.player.control('play')
        util.DEBUG_LOG('New player offset: {0}'.format(self.offset))
        self.player._playVideo(offset, seeking=self.seeking)

    def seekAbsolute(self, seek=None):
        self.seekOnStart = seek or self.seekOnStart
        if self.seekOnStart:
            self.player.control('play')
            self.player.seekTime(self.seekOnStart / 1000.0)

    def closeSeekDialog(self):
        util.CRON.forceTick()
        if self.dialog:
            self.dialog.doClose()

    def onPlayBackStarted(self):
        if self.mode == self.MODE_ABSOLUTE:
            self.seekAbsolute()

        subs = self.player.video.selectedSubtitleStream()
        if subs:
            xbmc.sleep(100)
            self.player.showSubtitles(False)
            path = subs.getSubtitleServerPath()
            if path:
                util.DEBUG_LOG('Setting subtitle path: {0}'.format(path))
                self.player.setSubtitles(path)
            else:
                # util.TEST(subs.__dict__)
                # util.TEST(self.player.video.mediaChoice.__dict__)
                util.DEBUG_LOG('Enabling embedded subtitles at: {0}'.format(subs.index))
                util.DEBUG_LOG('Kodi reported subtitles: {0}'.format(self.player.getAvailableSubtitleStreams()))
                self.player.setSubtitleStream(subs.index.asInt())

            self.player.showSubtitles(True)

        self.seeking = self.NO_SEEK

    def onPlayBackResumed(self):
        self.closeSeekDialog()

    def onPlayBackStopped(self):
        if self.seeking != self.SEEK_PLAYLIST:
            self.closeSeekDialog()

        if self.seeking not in (self.SEEK_IN_PROGRESS, self.SEEK_PLAYLIST):
            self.player.close()

    def onPlayBackEnded(self):
        if self.next():
            return

        if self.seeking != self.SEEK_PLAYLIST:
            self.closeSeekDialog()

        if self.seeking not in (self.SEEK_IN_PROGRESS, self.SEEK_PLAYLIST):
            self.player.close()

    def onPlayBackSeek(self, time, offset):
        if self.seekOnStart:
            self.seekOnStart = 0
            return

        self.seeking = self.SEEK_INIT
        self.player.control('pause')
        self.updateOffset()
        self.showSeekDialog(from_seek=True)

    def updateOffset(self):
        self.offset = int(self.player.getTime() * 1000)

    def onPlayBackFailed(self):
        self.seeking = self.NO_SEEK
        self.player.close()
        return True

    def onSeekOSD(self):
        if self.dialog.isOpen:
            self.closeSeekDialog()
            self.showSeekDialog()

    def onVideoWindowClosed(self):
        self.closeSeekDialog()
        if not self.seeking:
            self.player.stop()
            self.player.close()

    def onVideoOSD(self):
        # xbmc.executebuiltin('Dialog.Close(seekbar,true)')  # Doesn't work :)
        # if not self.seeking:
        self.showSeekDialog()

    def tick(self):
        self.dialog.tick()

    def close(self):
        self.closeSeekDialog()


class AudioPlayerHandler(BasePlayerHandler):
    def __init__(self, player, window=None):
        BasePlayerHandler.__init__(self, player)
        self.window = window

    def onPlayBackStopped(self):
        self.closeWindow()

    def onPlayBackEnded(self):
        self.closeWindow()

    def onPlayBackFailed(self):
        return True

    def closeWindow(self):
        if not self.window:
            return

        self.window.doClose()
        del self.window
        self.window = None


class PlexPlayer(xbmc.Player):
    def init(self):
        self._closed = False
        self.started = False
        self.video = None
        self.hasOSD = False
        self.hasSeekOSD = False
        self.xbmcMonitor = xbmc.Monitor()
        self.handler = BasePlayerHandler(self)
        self.playerBackground = None
        self.seekStepsSetting = util.SettingControl('videoplayer.seeksteps', 'Seek steps', disable_value=[-10, 10])
        self.seekDelaySetting = util.SettingControl('videoplayer.seekdelay', 'Seek delay', disable_value=0)
        self.thread = None
        if xbmc.getCondVisibility('Player.HasMedia'):
            self.started = True

        return self

    def open(self):
        self._closed = False
        self.monitor()

    def close(self, shutdown=False):
        self._closed = True
        if self.playerBackground:
            self.playerBackground.close()

    def reset(self):
        self.started = False
        self.handler = None

    def control(self, cmd):
        if cmd == 'play':
            util.DEBUG_LOG('Player - Control:  Command=Play')
            if xbmc.getCondVisibility('Player.Paused | !Player.Playing'):
                util.DEBUG_LOG('Player - Control:  Playing')
                xbmc.executebuiltin('PlayerControl(Play)')
        elif cmd == 'pause':
            util.DEBUG_LOG('Player - Control:  Command=Pause')
            if not xbmc.getCondVisibility('Player.Paused'):
                util.DEBUG_LOG('Player - Control:  Pausing')
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
        self.handler = SeekPlayerHandler(self)
        self.video = video
        self.open()
        self._playVideo(resume and video.viewOffset.asInt() or 0)

    def _playVideo(self, offset=0, seeking=0):
        pobj = plexplayer.PlexPlayer(self.video, offset)
        meta = pobj.build()
        url = meta.streamUrls[0]
        bifURL = pobj.getBifUrl()
        util.DEBUG_LOG('Playing URL(+{1}ms): {0}{2}'.format(url, offset, bifURL and ' - indexed' or ''))
        self.handler.setup(self.video.duration.asInt(), offset, bifURL, title=self.video.grandparentTitle, title2=self.video.title, seeking=seeking)
        url += '&X-Plex-Platform=Chrome'
        li = xbmcgui.ListItem(self.video.title, path=url, thumbnailImage=self.video.defaultThumb.asTranscodedImageURL(256, 256))
        li.setInfo('video', {'mediatype': self.video.type})
        self.play(url, li)

        if offset and not meta.isTranscoded:
            self.handler.seekOnStart = meta.playStart * 1000
            self.handler.mode = self.handler.MODE_ABSOLUTE
        else:
            self.handler.mode = self.handler.MODE_RELATIVE

    def playVideoPlaylist(self, playlist, startpos=-1, resume=True, handler=None):
        if not handler:
            self.handler = SeekPlayerHandler(self)
        self.handler.playlistPos = startpos
        self.handler.playlist = playlist
        self.video = playlist.items()[startpos]
        self.open()
        self._playVideo(resume and self.video.viewOffset.asInt() or 0, seeking=handler and handler.SEEK_PLAYLIST or 0)

    def createVideoListItem(self, video, index=0):
        url = 'plugin://script.plex/play?{0}'.format(base64.urlsafe_b64encode(video.serialize()))
        li = xbmcgui.ListItem(self.video.title, path=url, thumbnailImage=self.video.defaultThumb.asTranscodedImageURL(256, 256))
        li.setInfo('video', {
            'mediatype': self.video.type,
            'playcount': index,
            'comment': 'PLEX-{0}'.format(video.ratingKey)
        })

        return url, li

    def playAudio(self, track, window=None, fanart=None):
        self.handler = AudioPlayerHandler(self, window)
        url, li = self.createTrackListItem(track, fanart)
        self.play(url, li)

    def playAlbum(self, album, startpos=-1, window=None, fanart=None):
        self.handler = AudioPlayerHandler(self, window)
        plist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        plist.clear()
        index = 1
        for track in album.tracks():
            url, li = self.createTrackListItem(track, fanart, index=index)
            plist.add(url, li)
            index += 1
        xbmc.executebuiltin('PlayerControl(RandomOff)')
        self.play(plist, startpos=startpos)

    def playAudioPlaylist(self, playlist, startpos=-1, window=None, fanart=None):
        self.handler = AudioPlayerHandler(self, window)
        plist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        plist.clear()
        index = 1
        for track in playlist.items():
            url, li = self.createTrackListItem(track, fanart, index=index)
            plist.add(url, li)
            index += 1
        xbmc.executebuiltin('PlayerControl(RandomOff)')
        self.play(plist, startpos=startpos)

    def createTrackListItem(self, track, fanart=None, index=0):
        # pobj = plexplayer.PlexAudioPlayer(track)
        # url = pobj.build()['url']  # .streams[0]['url']
        # util.DEBUG_LOG('Playing URL: {0}'.format(url))
        # url += '&X-Plex-Platform=Chrome'
        url = 'plugin://script.plex/play?{0}'.format(base64.urlsafe_b64encode(track.serialize()))
        li = xbmcgui.ListItem(track.title, path=url, thumbnailImage=track.defaultThumb.asTranscodedImageURL(256, 256))
        li.setInfo('music', {
            'artist': str(track.grandparentTitle),
            'title': str(track.title),
            'album': str(track.parentTitle),
            'discnumber': track.parentIndex.asInt(),
            'tracknumber': track.get('index').asInt(),
            'duration': int(track.duration.asInt() / 1000),
            'playcount': index,
            'comment': 'PLEX-{0}'.format(track.ratingKey)
        })
        if fanart:
            li.setArt({'fanart': fanart})
        return (url, li)

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
            util.showNotification('Playback Failed!')
            # xbmcgui.Dialog().ok('Failed', 'Playback failed')

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

    def onSeekOSD(self):
        util.DEBUG_LOG('Player: Seek OSD opened')
        try:
            self.handler.onSeekOSD()
        except:
            util.ERROR()

    def stopAndWait(self):
        if self.isPlayingVideo():
            util.DEBUG_LOG('Player (Recording): Stopping for external wait')
            self.stop()
            self.handler.waitForStop()

    def monitor(self):
        if not self.thread or not self.thread.isAlive():
            self.thread = threading.Thread(target=self._monitor, name='PLAYER:MONITOR')
            self.thread.start()

    def _monitor(self):
        with playerbackground.PlayerBackgroundContext(
            background=self.video.art.asTranscodedImageURL(1920, 1080, blur=128, opacity=60, background=colors.noAlpha.Background)
        ) as self.playerBackground:
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
                            if xbmc.getCondVisibility('Window.IsActive(videoosd) | Player.ShowInfo'):
                                if not self.hasOSD:
                                    self.hasOSD = True
                                    self.onVideoOSD()
                            else:
                                self.hasOSD = False

                            if xbmc.getCondVisibility('Window.IsActive(seekbar)'):
                                if not self.hasSeekOSD:
                                    self.hasSeekOSD = True
                                    self.onSeekOSD()
                            else:
                                self.hasSeekOSD = False

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
