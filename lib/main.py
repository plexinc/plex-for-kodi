import plex
from windows import background, userselect
import backgroundthread


def main():
    back = background.BackgroundWindow.create()
    background.setSplash()

    try:
        if plex.init():
            if plex.PLEX.multiuser:
                background.setSplash(False)
                user, pin = userselect.getUser()
                if not user:
                    return
                background.setBusy()
                plex.switchUser(user, pin)

            print plex.PLEX
    finally:
        backgroundthread.BGThreader.shutdown()
        background.setBusy(False)
        background.setSplash(False)
        back.doClose()
        del back
