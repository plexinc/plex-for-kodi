import xbmc
from plexapi import myplex
from plexapi import exceptions
import util

PLEX = None
BASE = None
OWNED = False

USER = None


def init():
    util.DEBUG_LOG('Initializing...')
    global PLEX, OWNED, USER

    token_user = getToken()

    if not token_user:
        return False

    token, USER = token_user

    USER = USER or myplex.MyPlexUser.tokenSignin(token)
    if not USER:
        util.DEBUG_LOG('SIGN IN: Failed to sign in')
        return False

    testservers = sorted(servers(), key=lambda x: x.owned, reverse=True)
    print testservers

    for sr in testservers:
        try:
            util.DEBUG_LOG('Attemting to connect to: {0}'.format(sr.name))
            PLEX = sr.connect()
            _setBase(PLEX)
            OWNED = sr.owned
            break
        except exceptions.NotFound, e:
            util.DEBUG_LOG('SIGN IN: Connection error: {0}'.format(e.message))

    if not PLEX:
        util.messageDialog('Connection Error', u'Unable to connect to any servers')
        util.DEBUG_LOG('SIGN IN: Failed to connect to any servers')
        return False

    util.DEBUG_LOG('SIGN IN: Connected to server')
    return True


def initSingleUser():
    global PLEX
    lastID = util.getSetting('last.server.{0}'.format(USER.id))
    if lastID and lastID != PLEX.machineIdentifier:
        PLEX = getServer(USER, lastID) or PLEX


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


def getServer(user, ID=None, owned=False):
    serverResource = None
    if ID:
        try:
            serverResource = user.getResourceByID(ID)
        except:
            util.ERROR()

    if not serverResource:
        serverResource = user.getFirstServer(owned=owned)
        ID = serverResource.clientIdentifier

    try:
        server = serverResource and serverResource.connect() or None
        util.setSetting('last.server.{0}'.format(user.id), ID)
        return server
    except exceptions.NotFound, e:
        util.messageDialog('Connection Error', u'Unable to connect to {0}'.format(serverResource.name))
        util.DEBUG_LOG('Connection error: {0}'.format(e.message))


def switchUser(new_user, pin):
    global PLEX, USER

    USER = myplex.MyPlexUser.switch(new_user, pin)
    ID = util.getSetting('last.server.{0}'.format(USER.id))

    PLEX = getServer(USER, ID) or PLEX


def changeServer(server):
    global PLEX

    try:
        PLEX = server.connect()
        util.setSetting('last.server.{0}'.format(USER.id), server.clientIdentifier)
        return True
    except exceptions.NotFound, e:
        util.messageDialog('Connection Error', u'Unable to connect to {0}'.format(server.name))
        util.DEBUG_LOG('Connection error: {0}'.format(e.message))

    return False


def signOut():
    util.DEBUG_LOG('Signing out')
    global PLEX, BASE, USER, OWNED
    util.setSetting('auth.token', '')
    PLEX = None
    BASE = None
    USER = None
    OWNED = False
