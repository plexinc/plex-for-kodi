# -*- coding: utf-8 -*-
import http
from threading import Thread
from xml.etree import ElementTree
import time

import plexobjects
import plexresource
import exceptions
import util

import video
import audio
import photo

video, audio, photo  # Hides warning message


class PinLogin(object):
    INIT = 'https://my.plexapp.com/pins.xml'
    POLL = 'https://my.plexapp.com/pins/{0}.xml'
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
        response = http.POST(self.INIT)
        if response.status_code != http.codes.created:
            codename = http.status_codes.get(response.status_code)[0]
            raise exceptions.BadRequest('({0}) {1}'.format(response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf-8'))
        self.pin = data.find('code').text
        self.id = data.find('id').text

    def _poll(self):
        try:
            start = time.time()
            while not self._abort and time.time() - start < 300:
                response = http.GET(self.POLL.format(self.id))
                if response.status_code != http.codes.ok:
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


class MyPlexUser(plexobjects.PlexObject):
    """ Logs into my.plexapp.com to fetch account and token information. This
        useful to get a token if not on the local network.
    """
    SIGNIN = 'https://my.plexapp.com/users/sign_in.xml'

    def resources(self):
        return plexresource.fetchResources(self.authenticationToken)

    def getResource(self, search, port=32400):
        """ Searches server.name, server.sourceTitle and server.host:server.port
            from the list of available for this PlexUser.
        """
        return plexresource.findResource(self.resources(), search, port)

    def getResourceByID(self, ID):
        """ Searches by server.clientIdentifier
            from the list of available for this PlexUser.
        """
        return plexresource.findResourceByID(self.resources(), ID)

    # def devices(self):
    #     return MyPlexDevice.fetchResources(self.authenticationToken)

    @classmethod
    def processResponse(cls, response):
        if response.status_code != http.codes.created:
            codename = http.status_codes.get(response.status_code)[0]
            if response.status_code == 401:
                raise exceptions.Unauthorized('({0}) {1}'.format(response.status_code, codename))
            raise exceptions.BadRequest('({0}) {1}'.format(response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return cls(data)

    @classmethod
    def signin(cls, username, password):
        if 'X-Plex-Token' in util.BASE_HEADERS:
            del util.BASE_HEADERS['X-Plex-Token']
        auth = (username, password)
        util.LOG('POST {0}'.format(cls.SIGNIN))
        response = http.POST(cls.SIGNIN, auth=auth)
        return cls.processResponse(response)

    @classmethod
    def tokenSignin(cls, auth_token):
        if 'X-Plex-Token' in util.BASE_HEADERS:
            del util.BASE_HEADERS['X-Plex-Token']
        util.LOG('POST {0}'.format(cls.SIGNIN))
        response = http.POST(cls.SIGNIN, params={'auth_token': auth_token})
        return cls.processResponse(response)

    @classmethod
    def switch(cls, user, pin=None):
        token = MyPlexHomeUser.getSwitchToken(user, pin)
        if not token:
            return None
        util.BASE_HEADERS['X-Plex-Token'] = token
        util.LOG('POST {0}'.format(cls.SIGNIN))
        response = http.POST(cls.SIGNIN)
        return cls.processResponse(response)


class MyPlexHomeUser(plexobjects.PlexObject):
    USERS = 'https://plex.tv/api/home/users'
    SWITCH = 'https://plex.tv/api/home/users/{0}/switch?pin={1}'

    def __repr__(self):
        return '<{1}:{1}:{2}>'.format(self.__class__.__name__, self.id, self.title.encode('utf8'))

    @classmethod
    def getSwitchToken(cls, user, pin=None):
        response = http.POST(cls.SWITCH.format(user.id, pin or ''))
        if response.status_code != http.codes.created:
            codename = http.status_codes.get(response.status_code)[0]
            if response.status_code == 401:
                raise exceptions.Unauthorized('({0}) {1}'.format(response.status_code, codename))
            raise exceptions.BadRequest('({0}) {1}'.format(response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return data.attrib.get('authenticationToken')

    @classmethod
    def fetchUsers(cls, token):
        headers = util.BASE_HEADERS
        headers['X-Plex-Token'] = token
        util.LOG('GET {0}?X-Plex-Token={1}'.format(cls.USERS, token))
        response = http.GET(cls.USERS)
        data = ElementTree.fromstring(response.text.encode('utf8'))
        return [MyPlexHomeUser(elem) for elem in data]


# TODO: Is this a plex client in disguise?
# class MyPlexDevice(object):
#     DEVICES = 'https://plex.tv/devices.xml'

#     def __init__(self, data):
#         self.name = data.attrib.get('name')
#         self.publicAddress = data.attrib.get('publicAddress')
#         self.product = data.attrib.get('product')
#         self.productVersion = data.attrib.get('productVersion')
#         self.platform = data.attrib.get('platform')
#         self.platformVersion = data.attrib.get('platformVersion')
#         self.device = data.attrib.get('device')
#         self.model = data.attrib.get('model')
#         self.vendor = data.attrib.get('vendor')
#         self.provides = data.attrib.get('provides').split(',')
#         self.clientIdentifier = data.attrib.get('clientIdentifier')
#         self.version = data.attrib.get('version')
#         self.id = data.attrib.get('id')
#         self.token = data.attrib.get('token')
#         self.screenResolution = data.attrib.get('screenResolution')
#         self.screenDensity = data.attrib.get('screenDensity')
#         self.connectionsUris = [connection.attrib.get('uri') for connection in data.iter('Connection')]

#     def __repr__(self):
#         return '<%s:%s:%s>' % (self.__class__.__name__, self.name.encode('utf8'), self.product.encode('utf8'))

#     @property
#     def isReachable(self):
#         return len(self.connectionsUris)

#     @property
#     def baseUrl(self):
#         if not self.isReachable:
#             raise Exception('This device is not reachable')
#         return self.connectionsUris[0]

#     @classmethod
#     def fetchResources(cls, token):
#         headers = plexapi.BASE_HEADERS
#         headers['X-Plex-Token'] = token
#         log.info('GET %s?X-Plex-Token=%s', cls.DEVICES, token)
#         response = requests.get(cls.DEVICES, headers=headers, timeout=TIMEOUT)
#         data = ElementTree.fromstring(response.text.encode('utf8'))
#         return [MyPlexDevice(elem) for elem in data]

#     def sendCommand(self, command, args=None):
#         url = '%s%s' % (self.url(command), utils.joinArgs(args))
#         log.info('GET %s', url)
#         headers = plexapi.BASE_HEADERS
#         headers['X-Plex-Target-Client-Identifier'] = self.clientIdentifier
#         response = requests.get(url, headers=headers, timeout=TIMEOUT)
#         if response.status_code != requests.codes.ok:
#             codename = codes.get(response.status_code)[0]
#             raise BadRequest('(%s) %s' % (response.status_code, codename))
#         data = response.text.encode('utf8')
#         if data:
#             try:
#                 return ElementTree.fromstring(data)
#             except:
#                 pass
#         return None

#     def url(self, path):
#         return '%s/player/%s' % (self.baseUrl, path.lstrip('/'))

#     # Navigation Commands
#     def moveUp(self, args=None): self.sendCommand('navigation/moveUp', args)  # noqa
#     def moveDown(self, args=None): self.sendCommand('navigation/moveDown', args)  # noqa
#     def moveLeft(self, args=None): self.sendCommand('navigation/moveLeft', args)  # noqa
#     def moveRight(self, args=None): self.sendCommand('navigation/moveRight', args)  # noqa
#     def pageUp(self, args=None): self.sendCommand('navigation/pageUp', args)  # noqa
#     def pageDown(self, args=None): self.sendCommand('navigation/pageDown', args)  # noqa
#     def nextLetter(self, args=None): self.sendCommand('navigation/nextLetter', args)  # noqa
#     def previousLetter(self, args=None): self.sendCommand('navigation/previousLetter', args)  # noqa
#     def select(self, args=None): self.sendCommand('navigation/select', args)  # noqa
#     def back(self, args=None): self.sendCommand('navigation/back', args)  # noqa
#     def contextMenu(self, args=None): self.sendCommand('navigation/contextMenu', args)  # noqa
#     def toggleOSD(self, args=None): self.sendCommand('navigation/toggleOSD', args)  # noqa

#     # Playback Commands
#     def play(self, args=None): self.sendCommand('playback/play', args)  # noqa
#     def pause(self, args=None): self.sendCommand('playback/pause', args)  # noqa
#     def stop(self, args=None): self.sendCommand('playback/stop', args)  # noqa
#     def stepForward(self, args=None): self.sendCommand('playback/stepForward', args)  # noqa
#     def bigStepForward(self, args=None): self.sendCommand('playback/bigStepForward', args)  # noqa
#     def stepBack(self, args=None): self.sendCommand('playback/stepBack', args)  # noqa
#     def bigStepBack(self, args=None): self.sendCommand('playback/bigStepBack', args)  # noqa
#     def skipNext(self, args=None): self.sendCommand('playback/skipNext', args)  # noqa
#     def skipPrevious(self, args=None): self.sendCommand('playback/skipPrevious', args)  # noqa
