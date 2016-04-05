import xbmc
from plexapi import myplex
import util

PLEX = None


def init():
    global PLEX

    token_user = getToken()

    if not token_user:
        return False

    token, user = token_user
    print repr(token)
    user = user or myplex.MyPlexUser.tokenSignin(token)
    if not user:
        util.DEBUG_LOG('SIGN IN: Failed to sign in')
        return False

    PLEX = user.getFirstServer(owned=True).connect()

    if not PLEX:
        util.DEBUG_LOG('SIGN IN: Failed to connect to server')
        return False

    util.DEBUG_LOG('SIGN IN: Connected to server')
    return True


def getToken():
    token_user = authorize()
    if token_user:
        util.setSetting('auth.token', token_user[0])
        return token_user
    else:
        util.DEBUG_LOG('SIGN IN: Failed to get initial token')

    return None


def authorize():
    token = util.getSetting('auth.token')
    if token:
        return (token, None)

    from windows import signin, background

    background.setSplash(False)

    back = signin.Background.create()

    pre = signin.PreSignInWindow.open()
    try:
        if not pre.doSignin:
            return None
    finally:
        del pre

    try:
        while True:
            pinLoginWindow = signin.PinLoginWindow.create()
            pl = myplex.PinLogin()
            pinLoginWindow.setPin(pl.pin)

            try:
                pl.startTokenPolling()
                while not pl.finished():
                    if pinLoginWindow.abort:
                        util.DEBUG_LOG('SIGN IN: Pin login aborted')
                        pl.abort()
                        return None
                    xbmc.sleep(100)
                else:
                    if not pl.expired():
                        if pl.authenticationToken:
                            pinLoginWindow.setLinking()
                            user = myplex.MyPlexUser.tokenSignin(pl.authenticationToken)
                            return (pl.authenticationToken, user)
                        else:
                            return None
            finally:
                pinLoginWindow.doClose()
                del pinLoginWindow

            if pl.expired():
                util.DEBUG_LOG('SIGN IN: Pin expired')
                expiredWindow = signin.ExpiredWindow.open()
                try:
                    if not expiredWindow.refresh:
                        util.DEBUG_LOG('SIGN IN: Pin refresh aborted')
                        return None
                finally:
                    del expiredWindow
    finally:
        back.doClose()
        del back


def switchUser(user, pin):
    global PLEX

    user = myplex.MyPlexUser.switch(user, pin)
    PLEX = user.getFirstServer().connect()
