# -*- coding: utf-8 -*-
"""
PlexServer
"""
import requests
from requests.status_codes import _codes as codes
from plexapi import BASE_HEADERS, TIMEOUT
from plexapi import log, utils
from plexapi import audio, video, photo, playlist  # noqa; required
from plexapi.compat import quote
from plexapi.client import Client
from plexapi.exceptions import BadRequest, NotFound, UnknownType
from plexapi.library import Library
from plexapi.myplex import MyPlexAccount
from plexapi.playqueue import PlayQueue
from xml.etree import ElementTree

TOTAL_QUERIES = 0
DEFAULT_BASEURI = 'http://localhost:32400'


class Hub(object):

    def __init__(self, server, data):
        self.server = server
        self._loadData(data)

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.hubIdentifier)

    def _loadData(self, data):
        self.hubKey = data.attrib.get('hubKey')
        self.type = data.attrib.get('type')
        self.hubIdentifier = data.attrib.get('hubIdentifier')
        self.size = int(data.attrib.get('size', 0))
        self.title = data.attrib.get('title')
        self.more = utils.cast(bool, data.attrib.get('more'))

        self.items = []
        for elem in data:
            try:
                self.items.append(utils.buildItem(self.server, elem, '/hubs'))
            except UnknownType:
                print 'Unkown hub item type({1}): {0}'.format(elem, elem.attrib.get('type'))


class PlexServer(object):

    def __init__(self, baseuri=None, token=None, session=None):
        self.baseuri = baseuri or DEFAULT_BASEURI
        self.token = token
        self.session = session or requests.Session()
        data = self._connect()
        self.friendlyName = data.attrib.get('friendlyName')
        self.machineIdentifier = data.attrib.get('machineIdentifier')
        self.myPlex = bool(data.attrib.get('myPlex') == '1')
        self.multiuser = bool(data.attrib.get('multiuser') == '1')
        self.synced = bool(data.attrib.get('synced') == '1')
        self.myPlexMappingState = data.attrib.get('myPlexMappingState')
        self.myPlexSigninState = data.attrib.get('myPlexSigninState')
        self.myPlexSubscription = data.attrib.get('myPlexSubscription')
        self.myPlexUsername = data.attrib.get('myPlexUsername')
        self.platform = data.attrib.get('platform')
        self.platformVersion = data.attrib.get('platformVersion')
        self.transcoderActiveVideoSessions = int(data.attrib.get('transcoderActiveVideoSessions', 0))
        self.transcoderPhoto = bool(data.attrib.get('transcoderPhoto') == '1')
        self.transcoderAudio = bool(data.attrib.get('transcoderAudio') == '1')
        self.updatedAt = int(data.attrib.get('updatedAt', 0))
        self.version = data.attrib.get('version')
        self.isSecure = self.baseuri.startswith('https://')

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.baseuri)

    def _connect(self):
        try:
            return self.query('/')
        except Exception as err:
            log.error('%s: %s', self.baseuri, err)
            raise NotFound('No server found at: %s' % self.baseuri)

    @property
    def library(self):
        if self.platform == 'cloudsync':
            return Library(self, None)
        else:
            return Library(self, self.query('/library/'))

    def account(self):
        data = self.query('/myplex/account')
        return MyPlexAccount(self, data)

    def clients(self):
        items = []
        for elem in self.query('/clients'):
            items.append(Client(self, elem))
        return items

    def client(self, name):
        for elem in self.query('/clients'):
            if elem.attrib.get('name').lower() == name.lower():
                return Client(self, elem)
        raise NotFound('Unknown client name: %s' % name)

    def createPlayQueue(self, item):
        return PlayQueue.create(self, item)

    def headers(self):
        headers = BASE_HEADERS
        if self.token:
            headers['X-Plex-Token'] = self.token
        return headers

    def playlists(self):
        return utils.listItems(self, '/playlists')

    def playlist(self, title=None):  # noqa
        for item in self.playlists():
            if item.title == title:
                return item
        raise NotFound('Invalid playlist title: %s' % title)

    def hubs(self, section=None, count=None):
        hubs = []

        q = '/hubs'
        params = {}
        if section:
            q = '/hubs/sections/%s' % section

        if count is not None:
            params = {'count': count}

        for elem in self.query(q, params=params):
            hubs.append(Hub(self, elem))
        return hubs

    def query(self, path, method=None, **kwargs):
        global TOTAL_QUERIES
        TOTAL_QUERIES += 1
        url = self.url(path)
        method = method or self.session.get
        log.info('%s %s', method.__name__.upper(), url)
        response = method(url, headers=self.headers(), timeout=TIMEOUT, **kwargs)
        if response.status_code not in [200, 201]:
            codename = codes.get(response.status_code)[0]
            raise BadRequest('(%s) %s' % (response.status_code, codename))
        data = response.text.encode('utf8')

        return ElementTree.fromstring(data) if data else None

    def search(self, query, mediatype=None):
        """ Searching within a library section is much more powerful. """
        items = utils.listItems(self, '/search?query=%s' % quote(query))
        if mediatype:
            return [item for item in items if item.type == mediatype]
        return items

    def sessions(self):
        return utils.listItems(self, '/status/sessions')

    # Ported from Roku code #################################
    def getLocalServerPort(self):
        # TODO(schuyler): The correct thing to do here is to iterate over local
        # connections and pull out the port. For now, we're always returning 32400.

        return "32400"

    def isRequestToServer(self, url):
        # if m.activeconnection = invalid then return false

        schemeAndHost = ''.join(self.baseuri.split(':', 2)[0:2])

        return url[:len(schemeAndHost)] == schemeAndHost

    def convertUrlToLoopBack(self, url):
        # If the URL starts with our server URL, replace it with 127.0.0.1:32400.
        if self.isRequestToServer(url):
            url = "http://127.0.0.1:32400" + url[len(self.baseuri) - 1:]

        return url

    def getImageTranscodeURL(self, path, width, height, extraopts=None):
        if not self.transcoderPhoto:
            return self.url(path)

        # Build up our parameters
        params = "&width=" + str(width) + "&height=" + str(height)

        if extraopts:
            for key in extraopts:
                params = params + "&" + key + "=" + str(extraopts[key])

        if "://" in path:
            imageUrl = self.convertUrlToLoopBack(path)
        else:
            imageUrl = "http://127.0.0.1:" + self.getLocalServerPort() + path

        path = "/photo/:/transcode?url=" + quote(imageUrl) + params

        # Try to use a better server to transcode for synced servers
        # TODO: Implement (ruuk)
        if self.synced:
            selectedServer = None  # PlexServerManager().GetTranscodeServer("photo")
            if selectedServer:
                return selectedServer.url(path)

        return self.url(path)
    #######################################################

    def url(self, path):
        if self.token:
            delim = '&' if '?' in path else '?'
            return '%s%s%sX-Plex-Token=%s' % (self.baseuri, path, delim, self.token)
        return '%s%s' % (self.baseuri, path)
