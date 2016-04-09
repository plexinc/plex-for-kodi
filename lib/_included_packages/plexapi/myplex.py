# -*- coding: utf-8 -*-
"""
PlexAPI MyPlex
"""
import plexapi
import requests
from plexapi import TIMEOUT, log, utils
from plexapi.exceptions import BadRequest, NotFound, Unauthorized
from plexapi.utils import cast, toDatetime
from requests.status_codes import _codes as codes
from threading import Thread
from xml.etree import ElementTree
import time


class PinLogin(object):
    INIT = 'https://my.plexapp.com/pins.xml'
    POLL = 'https://my.plexapp.com/pins/%s.xml'
    POLL_INTERVAL = 1

    def __init__(self, callback=None):
        self._callback = callback
        self.id = None
        self.pin = None
        self.authenticationToken = None
        self._finished = False
        self._abort = False
        self._expired = False
        self._init()

    def _init(self):
        response = requests.post(self.INIT, headers=plexapi.BASE_HEADERS)
        if response.status_code != requests.codes.created:
            codename = codes.get(response.status_code)[0]
            raise BadRequest('(%s) %s' % (response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf-8'))
        self.pin = data.find('code').text
        self.id = data.find('id').text

    def _poll(self):
        try:
            start = time.time()
            while not self._abort and time.time() - start < 300:
                response = requests.get(self.POLL % self.id, headers=plexapi.BASE_HEADERS)
                if response.status_code != requests.codes.ok:
                    self._expired = True
                    break
                data = ElementTree.fromstring(response.text.encode('utf-8'))
                token = data.find('auth_token').text
                if token:
                    self.authenticationToken = token
                    break
                time.sleep(self.POLL_INTERVAL)

            if self._callback:
                self._callback(self.authenticationToken)
        finally:
            self._finished = True

    def finished(self):
        return self._finished

    def expired(self):
        return self._expired

    def startTokenPolling(self):
        t = Thread(target=self._poll)
        t.start()
        return t

    def waitForToken(self):
        t = self.startTokenPolling()
        t.join()
        return self.authenticationToken

    def abort(self):
        self._abort = True


class MyPlexUser(object):
    """ Logs into my.plexapp.com to fetch account and token information. This
        useful to get a token if not on the local network.
    """
    SIGNIN = 'https://my.plexapp.com/users/sign_in.xml'

    def __init__(self, data, initpath=None):
        self.initpath = initpath
        self.email = data.attrib.get('email')
        self.id = data.attrib.get('id')
        self.thumb = data.attrib.get('thumb')
        self.username = data.attrib.get('username')
        self.title = data.attrib.get('title')
        self.cloudSyncDevice = data.attrib.get('cloudSyncDevice')
        self.authenticationToken = data.attrib.get('authenticationToken')
        self.queueEmail = data.attrib.get('queueEmail')
        self.queueUid = data.attrib.get('queueUid')

    def resources(self):
        return MyPlexResource.fetchResources(self.authenticationToken)

    def getResource(self, search, port=32400):
        """ Searches server.name, server.sourceTitle and server.host:server.port
            from the list of available for this PlexUser.
        """
        return _findResource(self.resources(), search, port)

    def getFirstServer(self, owned=False):
        for resource in self.resources():
            if resource.provides == 'server' and (not owned or resource.owned):
                return resource

    def devices(self):
        return MyPlexDevice.fetchResources(self.authenticationToken)

    @classmethod
    def processResponse(cls, response):
        if response.status_code != requests.codes.created:
            codename = codes.get(response.status_code)[0]
            if response.status_code == 401:
                raise Unauthorized('(%s) %s' % (response.status_code, codename))
            raise BadRequest('(%s) %s' % (response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return cls(data)

    @classmethod
    def signin(cls, username, password):
        if 'X-Plex-Token' in plexapi.BASE_HEADERS:
            del plexapi.BASE_HEADERS['X-Plex-Token']
        auth = (username, password)
        log.info('POST %s', cls.SIGNIN)
        response = requests.post(cls.SIGNIN, headers=plexapi.BASE_HEADERS, auth=auth, timeout=TIMEOUT)
        return cls.processResponse(response)

    @classmethod
    def tokenSignin(cls, auth_token):
        if 'X-Plex-Token' in plexapi.BASE_HEADERS:
            del plexapi.BASE_HEADERS['X-Plex-Token']
        log.info('POST %s', cls.SIGNIN)
        response = requests.post(cls.SIGNIN, headers=plexapi.BASE_HEADERS, params={'auth_token': auth_token}, timeout=TIMEOUT)
        return cls.processResponse(response)

    @classmethod
    def switch(cls, user, pin=None):
        token = MyPlexHomeUser.getSwitchToken(user, pin)
        if not token:
            return None
        plexapi.BASE_HEADERS['X-Plex-Token'] = token
        log.info('POST %s', cls.SIGNIN)
        response = requests.post(cls.SIGNIN, headers=plexapi.BASE_HEADERS, timeout=TIMEOUT)
        return cls.processResponse(response)


class MyPlexAccount(object):
    """ Represents myPlex account if you already have a connection to a server. """

    def __init__(self, server, data):
        self.authToken = data.attrib.get('authToken')
        self.username = data.attrib.get('username')
        self.mappingState = data.attrib.get('mappingState')
        self.mappingError = data.attrib.get('mappingError')
        self.mappingErrorMessage = data.attrib.get('mappingErrorMessage')
        self.signInState = data.attrib.get('signInState')
        self.publicAddress = data.attrib.get('publicAddress')
        self.publicPort = data.attrib.get('publicPort')
        self.privateAddress = data.attrib.get('privateAddress')
        self.privatePort = data.attrib.get('privatePort')
        self.subscriptionFeatures = data.attrib.get('subscriptionFeatures')
        self.subscriptionActive = data.attrib.get('subscriptionActive')
        self.subscriptionState = data.attrib.get('subscriptionState')

    def resources(self):
        return MyPlexResource.fetchResources(self.authToken)

    def users(self):
        return MyPlexHomeUser.fetchUsers(self.authToken)

    def getResource(self, search, port=32400):
        """ Searches server.name, server.sourceTitle and server.host:server.port
            from the list of available for this PlexAccount.
        """
        return _findResource(self.resources(), search, port)


class MyPlexResource(object):
    RESOURCES = 'https://plex.tv/api/resources?includeHttps=1'
    SSLTESTS = [(True, 'uri'), (False, 'http_uri')]

    def __init__(self, data):
        self.name = data.attrib.get('name')
        self.accessToken = data.attrib.get('accessToken')
        self.product = data.attrib.get('product')
        self.productVersion = data.attrib.get('productVersion')
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.device = data.attrib.get('device')
        self.clientIdentifier = data.attrib.get('clientIdentifier')
        self.createdAt = toDatetime(data.attrib.get('createdAt'))
        self.lastSeenAt = toDatetime(data.attrib.get('lastSeenAt'))
        self.provides = data.attrib.get('provides')
        self.owned = cast(bool, data.attrib.get('owned'))
        self.owner = data.attrib.get('sourceTitle')
        self.home = cast(bool, data.attrib.get('home'))
        self.synced = cast(bool, data.attrib.get('synced'))
        self.presence = cast(bool, data.attrib.get('presence'))
        self.sameNetwork = cast(bool, data.attrib.get('publicAddressMatches'))
        self.connections = [ResourceConnection(elem) for elem in data if elem.tag == 'Connection']

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.name.encode('utf8'))

    def connect(self, ssl=None):
        # Only check non-local connections unless we own the resource
        connections = sorted(self.connections, key=lambda c:c.local, reverse=True)
        if not self.owned:
            connections = [c for c in connections if c.local is False]
        # Try connecting to all known resource connections in parellel, but
        # only return the first server (in order) that provides a response.
        threads, results = [], []
        for testssl, attr in self.SSLTESTS:
            if ssl in [None, testssl]:
                for i in range(len(connections)):
                    uri = getattr(connections[i], attr)
                    args = (uri, results, len(results))
                    results.append(None)
                    threads.append(Thread(target=self._connect, args=args))
                    threads[-1].start()
        for thread in threads:
            thread.join()
        # At this point we have a list of result tuples containing (uri, PlexServer)
        # or (uri, None) in the case a connection could not be established.
        for uri, result in results:
            log.info('Testing connection: %s %s', uri, 'OK' if result else 'ERR')
        results = list(filter(None, [r[1] for r in results if r]))
        if not results:
            raise NotFound('Unable to connect to resource: %s' % self.name)
        log.info('Connecting to server: %s', results[0])
        return results[0]

    def _connect(self, uri, results, i):
        try:
            from plexapi.server import PlexServer
            results[i] = (uri, PlexServer(uri, self.accessToken))
        except NotFound:
            results[i] = (uri, None)

    @classmethod
    def fetchResources(cls, token):
        headers = plexapi.BASE_HEADERS
        headers['X-Plex-Token'] = token
        log.info('GET %s?X-Plex-Token=%s', cls.RESOURCES, token)
        response = requests.get(cls.RESOURCES, headers=headers, timeout=TIMEOUT)
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return [MyPlexResource(elem) for elem in data]


class MyPlexHomeUser(object):
    USERS = 'https://plex.tv/api/home/users'
    SWITCH = 'https://plex.tv/api/home/users/%s/switch?pin=%s'

    def __init__(self, data):
        self.id = data.attrib.get('id')
        self.title = data.attrib.get('title')
        self.username = data.attrib.get('username')
        self.email = data.attrib.get('email')
        self.thumb = data.attrib.get('thumb')
        self.admin = cast(bool, data.attrib.get('admin'))
        self.guest = cast(bool, data.attrib.get('guest'))
        self.restricted = cast(bool, data.attrib.get('restricted'))
        self.protected = cast(bool, data.attrib.get('protected'))

    def __repr__(self):
        return '<%s:%s:%s>' % (self.__class__.__name__, self.id, self.title.encode('utf8'))

    @classmethod
    def getSwitchToken(cls, user, pin=None):
        response = requests.post('https://plex.tv/api/home/users/%s/switch?pin=%s' % (user.id, pin or ''), headers=plexapi.BASE_HEADERS)
        if response.status_code != requests.codes.created:
            codename = codes.get(response.status_code)[0]
            if response.status_code == 401:
                raise Unauthorized('(%s) %s' % (response.status_code, codename))
            raise BadRequest('(%s) %s' % (response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return data.attrib.get('authenticationToken')

    @classmethod
    def fetchUsers(cls, token):
        headers = plexapi.BASE_HEADERS
        headers['X-Plex-Token'] = token
        log.info('GET %s?X-Plex-Token=%s', cls.USERS, token)
        response = requests.get(cls.USERS, headers=headers, timeout=TIMEOUT)
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return [MyPlexHomeUser(elem) for elem in data]


class ResourceConnection(object):

    def __init__(self, data):
        self.protocol = data.attrib.get('protocol')
        self.address = data.attrib.get('address')
        self.port = cast(int, data.attrib.get('port'))
        self.uri = data.attrib.get('uri')
        self.local = cast(bool, data.attrib.get('local'))

    @property
    def http_uri(self):
        return 'http://%s:%s' % (self.address, self.port)

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.uri.encode('utf8'))


# TODO: Is this a plex client in disguise?
class MyPlexDevice(object):
    DEVICES = 'https://plex.tv/devices.xml'

    def __init__(self, data):
        self.name = data.attrib.get('name')
        self.publicAddress = data.attrib.get('publicAddress')
        self.product = data.attrib.get('product')
        self.productVersion = data.attrib.get('productVersion')
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.device = data.attrib.get('device')
        self.model = data.attrib.get('model')
        self.vendor = data.attrib.get('vendor')
        self.provides = data.attrib.get('provides').split(',')
        self.clientIdentifier = data.attrib.get('clientIdentifier')
        self.version = data.attrib.get('version')
        self.id = data.attrib.get('id')
        self.token = data.attrib.get('token')
        self.screenResolution = data.attrib.get('screenResolution')
        self.screenDensity = data.attrib.get('screenDensity')
        self.connectionsUris = [connection.attrib.get('uri') for connection in data.iter('Connection')]

    def __repr__(self):
        return '<%s:%s:%s>' % (self.__class__.__name__, self.name.encode('utf8'), self.product.encode('utf8'))

    @property
    def isReachable(self):
        return len(self.connectionsUris)

    @property
    def baseUrl(self):
        if not self.isReachable:
            raise Exception('This device is not reachable')
        return self.connectionsUris[0]

    @classmethod
    def fetchResources(cls, token):
        headers = plexapi.BASE_HEADERS
        headers['X-Plex-Token'] = token
        log.info('GET %s?X-Plex-Token=%s', cls.DEVICES, token)
        response = requests.get(cls.DEVICES, headers=headers, timeout=TIMEOUT)
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return [MyPlexDevice(elem) for elem in data]

    def sendCommand(self, command, args=None):
        url = '%s%s' % (self.url(command), utils.joinArgs(args))
        log.info('GET %s', url)
        headers = plexapi.BASE_HEADERS
        headers['X-Plex-Target-Client-Identifier'] = self.clientIdentifier
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        if response.status_code != requests.codes.ok:
            codename = codes.get(response.status_code)[0]
            raise BadRequest('(%s) %s' % (response.status_code, codename))
        data = response.text.encode('utf8')
        if data:
            try:
                return ElementTree.fromstring(data)
            except:
                pass
        return None

    def url(self, path):
        return '%s/player/%s' % (self.baseUrl, path.lstrip('/'))

    # Navigation Commands
    def moveUp(self, args=None): self.sendCommand('navigation/moveUp', args)  # noqa
    def moveDown(self, args=None): self.sendCommand('navigation/moveDown', args)  # noqa
    def moveLeft(self, args=None): self.sendCommand('navigation/moveLeft', args)  # noqa
    def moveRight(self, args=None): self.sendCommand('navigation/moveRight', args)  # noqa
    def pageUp(self, args=None): self.sendCommand('navigation/pageUp', args)  # noqa
    def pageDown(self, args=None): self.sendCommand('navigation/pageDown', args)  # noqa
    def nextLetter(self, args=None): self.sendCommand('navigation/nextLetter', args)  # noqa
    def previousLetter(self, args=None): self.sendCommand('navigation/previousLetter', args)  # noqa
    def select(self, args=None): self.sendCommand('navigation/select', args)  # noqa
    def back(self, args=None): self.sendCommand('navigation/back', args)  # noqa
    def contextMenu(self, args=None): self.sendCommand('navigation/contextMenu', args)  # noqa
    def toggleOSD(self, args=None): self.sendCommand('navigation/toggleOSD', args)  # noqa

    # Playback Commands
    def play(self, args=None): self.sendCommand('playback/play', args)  # noqa
    def pause(self, args=None): self.sendCommand('playback/pause', args)  # noqa
    def stop(self, args=None): self.sendCommand('playback/stop', args)  # noqa
    def stepForward(self, args=None): self.sendCommand('playback/stepForward', args)  # noqa
    def bigStepForward(self, args=None): self.sendCommand('playback/bigStepForward', args)  # noqa
    def stepBack(self, args=None): self.sendCommand('playback/stepBack', args)  # noqa
    def bigStepBack(self, args=None): self.sendCommand('playback/bigStepBack', args)  # noqa
    def skipNext(self, args=None): self.sendCommand('playback/skipNext', args)  # noqa
    def skipPrevious(self, args=None): self.sendCommand('playback/skipPrevious', args)  # noqa


def _findResource(resources, search, port=32400):
    """ Searches server.name """
    search = search.lower()
    log.info('Looking for server: %s', search)
    for server in resources:
        if search == server.name.lower():
            log.info('Server found: %s', server)
            return server
    log.info('Unable to find server: %s', search)
    raise NotFound('Unable to find server: %s' % search)
