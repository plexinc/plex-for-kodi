import threading

import xbmc

from plexapi import myplex
from plexapi import exceptions
import util

PLEX = None
BASE = None

USER = None
SEVERMANAGER = None


class ServerManager(object):
    def __init__(self):
        self._abort = False
        self._thread = None
        self._hasOwned = False
        self._testing = threading.Event()
        self._testing.set()

        self.reInit()

    def reInit(self):
        self._hasOwned = False
        self.serverResources = self.getServerResources()
        self.validServers = []
        self.failedServers = []

        for sr in self.serverResources:
            self._hasOwned = sr.owned or self._hasOwned
            util.DEBUG_LOG('Server Resources:')
            util.DEBUG_LOG('  Server: {0}'.format(sr))
            util.DEBUG_LOG('    Owned: {0}'.format(sr.owned))
            util.DEBUG_LOG('    Local: {0}'.format(sr.owned))
            util.DEBUG_LOG('    Connections: {0}'.format(sr.connections))

    def getServerResources(self):
        return sorted([s for s in USER.resources() if s.provides == 'server'], key=lambda x: x.owned, reverse=True)

    def testServers(self):
        self._thread = threading.Thread(target=self._testServers)
        self._thread.start()

    def _testServers(self):
        util.DEBUG_LOG('Testing servers: START')
        self._testing.clear()
        try:
            self.validServers = []
            self.failedServers = []

            testThreads = []

            for sr in self.serverResources:
                if self._abort or xbmc.abortRequested:
                    break
                testThreads.append(threading.Thread(target=self._testServer, args=(sr,)))
                testThreads[-1].start()

            for t in testThreads:
                t.join()

        finally:
            self._testing.set()

        util.DEBUG_LOG('Testing servers: DONE')

    def _testServer(self, sr):
        try:
            util.DEBUG_LOG('Attemting to connect to: {0}'.format(sr.name))
            self.validServers.append(sr.connect(ssl=True))
        except exceptions.NotFound, e:
            try:
                self.validServers.append(sr.connect(ssl=False))
            except exceptions.NotFound, e:
                util.DEBUG_LOG('Connection error: {0}'.format(e.message))
                self.failedServers.append(sr)

    def start(self):
        self.finish()
        self.testServers()
        return self

    def abort(self):
        self._abort = True

    def getServerByID(self, ID, wait=False):
        server = self._getServerByID(ID)
        if server:
            return server

        if wait and not self._testing.isSet():
            util.DEBUG_LOG('Waiting for preferred server...')
            # Otherwise, if we're in the middle of testing, wait 5 mins while checking
            for x in range(25):
                server = self._getServerByID(ID)
                if server:
                    return server
                if self._testing.wait(0.2):
                    # Testing is done so return what we have
                    return self._getServerByID(ID)

        return None

    def _getServerByID(self, ID):
        # See if we already have it in valid servers
        for server in self.validServers:
            if server.machineIdentifier == ID:
                return server
        else:
            # If it's in the failed servers, give up
            for server in self.failedServers:
                if server.machineIdentifier == ID:
                    return None

        return None

    def getServer(self):
        util.DEBUG_LOG('Waiting for server connection...')
        while not self._abort and not xbmc.abortRequested and self._thread.isAlive():
            if self.validServers:
                break
            xbmc.sleep(100)

        if self._hasOwned:
            util.DEBUG_LOG('Waiting for an owned server...')
            for x in range(10):
                if self._abort or xbmc.abortRequested or not self._thread.isAlive():
                    break
                for s in self.validServers:
                    if s.owned:
                        return s
                    xbmc.sleep(100)

        return self.validServers and self.validServers[0] or None

    def finish(self):
        self.abort()
        if self._thread and self._thread.isAlive():
            util.DEBUG_LOG('Waiting on server testing thread...')
            self._thread.join()
        self._abort = False


def init():
    util.DEBUG_LOG('Initializing...')
    global PLEX, USER, SEVERMANAGER

    token_user = getToken()

    if not token_user:
        return False

    token, USER = token_user

    USER = USER or myplex.MyPlexUser.tokenSignin(token)
    if not USER:
        util.DEBUG_LOG('SIGN IN: Failed to sign in')
        return False

    SEVERMANAGER = ServerManager().start()
    PLEX = SEVERMANAGER.getServer()
    _setBase(PLEX)

    if not PLEX:
        util.messageDialog('Connection Error', u'Unable to connect to any servers')
        util.DEBUG_LOG('SIGN IN: Failed to connect to any servers')
        return False

    util.DEBUG_LOG('SIGN IN: Connected to server: {0} - {1}'.format(PLEX.friendlyName, PLEX.baseuri))
    return True


def initSingleUser():
    global PLEX
    lastID = util.getSetting('last.server.{0}'.format(USER.id))
    if lastID and lastID != PLEX.machineIdentifier:
        PLEX = SEVERMANAGER.getServerByID(lastID, wait=True) or PLEX


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


def switchUser(new_user, pin):
    global PLEX, USER

    USER = myplex.MyPlexUser.switch(new_user, pin)
    ID = util.getSetting('last.server.{0}'.format(USER.id))

    if ID and PLEX.machineIdentifier != ID:
        PLEX = SEVERMANAGER.getServerByID(ID, wait=True) or PLEX


def changeServer(server):
    global PLEX

    PLEX = server
    util.setSetting('last.server.{0}'.format(USER.id), server.machineIdentifier)
    return True


def signOut():
    util.DEBUG_LOG('Signing out')
    global PLEX, BASE, USER
    util.setSetting('auth.token', '')
    PLEX = None
    BASE = None
    USER = None
