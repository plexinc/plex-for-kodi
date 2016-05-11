import threading

import xbmc

from plexapi import myplex
from plexapi import exceptions
import util

PLEX = None
BASE = None

USER = None
SERVERMANAGER = None


class ServerTester(object):
    def __init__(self):
        self._abort = False
        self.validServers = []
        self.failedServers = []
        self.init()

    def init(self):
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

        self._thread = threading.Thread(target=self._testServers)
        self._thread.start()

    def isRunning(self, wait=None):
        if not self._thread.isAlive():
            return False

        if wait:
            self._thread.join(wait)

        return self._thread.isAlive()

    def wait(self):
        if not self.isRunning():
            return
        self._thread.join()

    def abort(self):
        self._abort = True

    def getServerResources(self):
        return sorted([s for s in USER.resources() if s.provides == 'server'], key=lambda x: x.owned, reverse=True)

    def _testServers(self):
        util.DEBUG_LOG('Testing servers: START')
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


class ServerManager(object):
    def __init__(self):
        self._abort = False
        self._currentTest = None
        self._oldTests = []

    def testServers(self):
        if self._currentTest and self._currentTest.isRunning():
            self._currentTest.abort()
            self._oldTests.append(self._currentTest)

        self._currentTest = ServerTester()

    def start(self):
        self.testServers()
        return self

    def reStart(self):
        self.start()

    def abort(self):
        self._abort = True
        self._currentTest.abort()
        for test in self._oldTests:
            test.abort()

    def getServerByID(self, ID, wait=False):
        server = self._getServerByID(ID)
        if server:
            return server

        if wait and self._currentTest.isRunning():
            util.DEBUG_LOG('Waiting for preferred server...')
            # Otherwise, if we're in the middle of testing, wait 5 mins while checking
            for x in range(25):
                server = self._getServerByID(ID)
                if server:
                    return server
                if self._currentTest.isRunning(wait=0.2):
                    # Testing is done so return what we have
                    return self._getServerByID(ID)

        return None

    def _getServerByID(self, ID):
        # See if we already have it in valid servers
        for server in self._currentTest.validServers:
            if server.machineIdentifier == ID:
                return server
        else:
            # If it's in the failed servers, give up
            for resource in self._currentTest.failedServers:
                if resource.clientIdentifier == ID:
                    return None

        return None

    def getServer(self):
        util.DEBUG_LOG('Waiting for server connection...')
        while not self._abort and not xbmc.abortRequested and self._currentTest.isRunning():
            if self._currentTest.validServers:
                break
            xbmc.sleep(100)

        if self._currentTest._hasOwned:
            util.DEBUG_LOG('Waiting for an owned server...')
            for x in range(10):
                if self._abort or xbmc.abortRequested or not self._currentTest.isRunning():
                    break
                for s in self._currentTest.validServers:
                    if s.owned:
                        return s
                    xbmc.sleep(100)

        return self._currentTest.validServers and self._currentTest.validServers[0] or None

    def validServers(self):
        return self._currentTest and self._currentTest.validServers or []

    def finish(self):
        self.abort()
        if self._currentTest:
            self._oldTests.append(self._currentTest)
            self._currentTest = None

        for test in self._oldTests:
            if test.isRunning():
                util.DEBUG_LOG('Waiting on server testing thread...')
                test.wait()


def init():
    util.DEBUG_LOG('Initializing...')
    global PLEX, USER, SERVERMANAGER

    token_user = getToken()

    if not token_user:
        return False

    token, USER = token_user

    util.DEBUG_LOG('SIGN IN: Signing in...')
    USER = USER or myplex.MyPlexUser.tokenSignin(token)
    if not USER:
        util.DEBUG_LOG('SIGN IN: Failed to sign in')
        return False

    util.DEBUG_LOG('SIGN IN: Signed in')

    SERVERMANAGER = ServerManager().start()
    PLEX = SERVERMANAGER.getServer()
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
        PLEX = SERVERMANAGER.getServerByID(lastID, wait=True) or PLEX


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

    util.DEBUG_LOG('USER SWITCH: Started')
    USER = myplex.MyPlexUser.switch(new_user, pin)
    ID = util.getSetting('last.server.{0}'.format(USER.id))
    util.DEBUG_LOG('USER SWITCH: Switched')

    util.DEBUG_LOG('USER SWITCH: Getting new server')
    SERVERMANAGER.reStart()

    PLEX = None
    if ID:
        PLEX = SERVERMANAGER.getServerByID(ID, wait=True)

    if not PLEX:
        PLEX = SERVERMANAGER.getServer()
    util.DEBUG_LOG('USER SWITCH: Finished')


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
