import opener


class UtilMixin():
    def __init__(self):
        self.exitCommand = None

    def processCommand(self, command):
        if command and command.startswith('HOME'):
            self.exitCommand = command
            self.doClose()

    def closeWithCommand(self, command):
        self.exitCommand = command
        self.doClose()

    def showAudioPlayer(self, **kwargs):
        import musicplayer
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow, **kwargs))
