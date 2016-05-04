import xbmc
from plexapi import myplex
import util

PLEX = None
BASE = None

USER = None


def init():
    global PLEX
    global USER

    token_user = getToken()

    if not token_user:
        return False

    token, USER = token_user

    USER = USER or myplex.MyPlexUser.tokenSignin(token)
    if not USER:
        util.DEBUG_LOG('SIGN IN: Failed to sign in')
        return False

    serverResource = USER.getFirstServer(owned=True)
    if not serverResource:
        serverResource - USER.getFirstServer()
    name = serverResource.name

    PLEX = serverResource.connect()
    _setBase(PLEX)

    if not PLEX:
        util.DEBUG_LOG('SIGN IN: Failed to connect to server')
        return False

    lastName = util.getSetting('last.server')
    if lastName and lastName != name:
        PLEX = getServer(USER, name)

    util.DEBUG_LOG('SIGN IN: Connected to server')
    return True


def _setBase(server):
    global BASE
    BASE = server


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


def servers():
    return [s for s in USER.resources() if s.provides == 'server']


def getServer(user, name=None, owned=False):
    serverResource = None
    if name:
        try:
            serverResource = user.getResource(name)
        except:
            util.ERROR()

    if not serverResource:
        serverResource = user.getFirstServer(owned=owned)
        name = serverResource.name
        util.setSetting('last.server', name)

    return serverResource and serverResource.connect()


def switchUser(new_user, pin):
    global PLEX
    global USER

    USER = myplex.MyPlexUser.switch(new_user, pin)
    name = util.getSetting('last.server')

    PLEX = getServer(USER, name)


def changeServer(server):
    global PLEX

    util.setSetting('last.server', server.name)

    PLEX = server.connect()
