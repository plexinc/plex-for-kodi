# -*- coding: utf-8 -*-
import http
import util
import exceptions
import compat

import plexobjects
import plexresource
import plexlibrary
import myplexaccount
# from plexapi.client import Client
# from plexapi.playqueue import PlayQueue


TOTAL_QUERIES = 0
DEFAULT_BASEURI = 'http://localhost:32400'


class Hub(plexobjects.PlexObject):
    def init(self, data):
        self.items = []
        for elem in data:
            try:
                self.items.append(plexobjects.buildItem(self.server, elem, '/hubs'))
            except exceptions.UnknownType:
                print 'Unkown hub item type({1}): {0}'.format(elem, elem.attrib.get('type'))

    def __repr__(self):
        return '<{0}:{1}>'.format(self.__class__.__name__, self.hubIdentifier)


class PlexServer(plexresource.PlexResource):

    def init(self, data):
        plexresource.PlexResource.init(self, data)
        self.server = self
        self.session = http.Session()

    def __repr__(self):
        return '<{0}:{1}>'.format(self.__class__.__name__, self.baseuri)

    def _connect(self):
        try:
            return self.query('/')
        except Exception as err:
            util.LOG('ERROR: {0} - {1}'.format(self.baseuri, err.message))
            raise exceptions.NotFound('No server found at: {0}'.format(self.baseuri))

    def library(self):
        if self.platform == 'cloudsync':
            return plexlibrary.Library(None, server=self)
        else:
            return plexlibrary.Library(self.query('/library/'), server=self)

    def account(self):
        data = self.query('/myplex/account')
        return myplexaccount.MyPlexAccount(self, data)

    # def clients(self):
    #     items = []
    #     for elem in self.query('/clients'):
    #         items.append(Client(self, elem))
    #     return items

    # def client(self, name):
    #     for elem in self.query('/clients'):
    #         if elem.attrib.get('name').lower() == name.lower():
    #             return Client(self, elem)
    #     raise exceptions.NotFound('Unknown client name: %s' % name)

    # def createPlayQueue(self, item):
    #     return PlayQueue.create(self, item)

    def playlists(self):
        return util.listItems(self, '/playlists')

    def playlist(self, title=None):  # noqa
        for item in self.playlists():
            if item.title == title:
                return item
        raise exceptions.NotFound('Invalid playlist title: %s' % title)

    def hubs(self, section=None, count=None):
        hubs = []

        q = '/hubs'
        params = {}
        if section:
            q = '/hubs/sections/%s' % section

        if count is not None:
            params = {'count': count}

        for elem in self.query(q, params=params):
            hubs.append(Hub(elem, server=self))
        return hubs

    def search(self, query, mediatype=None):
        """ Searching within a library section is much more powerful. """
        items = plexobjects.listItems(self, '/search?query=%s' % compat.quote(query))
        if mediatype:
            return [item for item in items if item.type == mediatype]
        return items

    def sessions(self):
        return plexobjects.listItems(self, '/status/sessions')

    def query(self, path, method=None, token=None, **kwargs):
        method = method or self.session.get
        return self.connection.query(path, method, token, **kwargs)

    def url(self, path):
        return self.connection.getUrl(path, self.token)

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

    def transcodedImageURL(self, path, width, height, extraopts=None):
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

        path = "/photo/:/transcode?url=" + compat.quote(imageUrl) + params

        # Try to use a better server to transcode for synced servers
        # TODO: Implement (ruuk)
        if self.synced.asBool():
            selectedServer = None  # PlexServerManager().GetTranscodeServer("photo")
            if selectedServer:
                return selectedServer.url(path)

        return self.url(path)
    #######################################################
