import opener

HOME = None


class UtilMixin():
    def __init__(self):
        self.exitCommand = None

    def goHome(self):
        HOME.show()
        self.closeWithCommand('HOME')

    def openWindow(self, window_class, **kwargs):
        self.processCommand(opener.handleOpen(window_class, **kwargs))

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


def shutdownHome(self):
    global HOME
    del HOME
