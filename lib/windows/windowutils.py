from lib import util
import opener
import dropdown

from lib.util import T


HOME = None


class UtilMixin():
    def __init__(self):
        self.exitCommand = None

    def goHome(self, section=None):
        HOME.show()
        if section:
            self.closeWithCommand('HOME:{0}'.format(section))
        else:
            self.closeWithCommand('HOME')

    def openItem(self, obj):
        self.processCommand(opener.open(obj))

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

    def getPlaylistResume(self, pl, items, title):
        resume = False
        watched = False
        for i in items:
            if (watched and not i.isWatched) or i.get('viewOffset').asInt():
                if i.get('viewOffset'):
                    choice = dropdown.showDropdown(
                        options=[
                            {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(util.timeDisplay(i.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                            {'key': 'play', 'display': T(32317, 'Play from beginning')}
                        ],
                        pos=(660, 441),
                        close_direction='none',
                        set_dropdown_prop=False,
                        header=u'{0} - {1}{2} \u2022 {3}{4}'.format(title, T(32310, 'S'), i.parentIndex, T(32311, 'E'), i.index)
                    )

                    if not choice:
                        return None

                    if choice['key'] == 'resume':
                        resume = True

                pl.setCurrent(i)
                break
            elif i.isWatched:
                watched = True
            else:
                break

        return resume


def shutdownHome():
    global HOME
    if HOME:
        HOME.shutdown()
    del HOME
    HOME = None
    HOME
