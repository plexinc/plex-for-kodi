import time
import threading
from xml.etree import ElementTree

import http
import exceptions
import plexobjects
import util

RESOURCES = 'https://plex.tv/api/resources?includeHttps=1'


class PlexResource(plexobjects.PlexObject):
    def init(self, data):
        self.connection = None
        self.connections = plexobjects.PlexItemList(data, ResourceConnection, 'Connection')

    def __repr__(self):
        return '<{0}:{1}>'.format(self.__class__.__name__, self.name.encode('utf8'))

    def setConnection(self, connection):
        self.connection = connection
        self._setData(connection.data)

    def connect(self):
        connections = sorted(self.connections(), key=lambda c: c.local)

        # Try connecting to all known resource connections in parellel, but
        # only return the first server (in order) that provides a response.
        threads = []
        for i, connection in enumerate(connections):
            threads.append(threading.Thread(target=connection.connect))
            threads[-1].start()

        alive = True
        while alive:
            alive = False
            for i, thread in enumerate(threads):
                if thread.is_alive():
                    alive = True
                else:
                    conn = connections[i]
                    if conn.reachable:
                        util.LOG('Using server connection: {0}'.format(conn))
                        self.setConnection(conn)
                        return
            time.sleep(0.1)

        reachable = [c for c in connections if c.reachable]
        if not reachable:
            raise exceptions.NotFound('No reachable resource connections: {0} ({1})'.format(self.name, self.clientIdentifier))

        secure = [c for c in reachable if c.secure]
        if secure:
            conn = secure[0]
        else:
            conn = reachable[0]

        util.LOG('Using server connection: {0}'.format(conn))
        self.setConnection(conn)


class ResourceConnection(plexobjects.PlexObject):
    def init(self, data):
        self.secure = True
        self.reachable = False
        self.data = None

    def __repr__(self):
        return '<{0}:{1}>'.format(self.__class__.__name__, self.uri.encode('utf8'))

    @property
    def http_uri(self):
        return 'http://{0}:{1}'.format(self.address, self.port)

    @property
    def URL(self):
        if self.secure:
            return self.uri
        else:
            return self.http_url

    def connect(self):
        util.LOG('Connecting: {0}'.format(self.URL))
        try:
            self.data = self.query('/')
            self.reachable = True
            return True
        except Exception as err:
            util.ERROR(self.URL, err)

        util.LOG('Connecting: Secure failed, trying insecure...')
        self.secure = False

        try:
            self.data = self.query('/')
            self.reachable = True
            return True
        except Exception as err:
            util.ERROR(self.URL, err)

        return False

    def headers(self, token=None):
        headers = util.BASE_HEADERS
        if token:
            headers['X-Plex-Token'] = token
        return headers

    def query(self, path, method=None, token=None, **kwargs):
        method = method or http.requests.get
        url = self.getURL(path)
        util.LOG('{0} {1}'.format(method.__name__.upper(), url))
        response = method(url, headers=self.headers(token), timeout=util.TIMEOUT, **kwargs)
        if response.status_code not in (200, 201):
            codename = http.codes.get(response.status_code)[0]
            raise exceptions.BadRequest('({0}) {1}'.format(response.status_code, codename))
        data = response.text.encode('utf8')

        return ElementTree.fromstring(data) if data else None

    def getURL(self, path, token=None):
        if token:
            delim = '&' if '?' in path else '?'
            return '{base}{path}{delim}X-Plex-Token={token}'.format(base=self.URL, path=path, delim=delim, token=token)
        return '{0}{1}'.format(self.URL, path)


def fetchResources(token):
    headers = util.BASE_HEADERS
    headers['X-Plex-Token'] = token
    util.LOG('GET {0}?X-Plex-Token={1}'.format(RESOURCES, token))
    response = http.GET(RESOURCES)
    data = ElementTree.fromstring(response.text.encode('utf8'))
    import plexserver
    return [plexserver.PlexServer(elem) for elem in data]


def findResource(resources, search, port=32400):
    """ Searches server.name """
    search = search.lower()
    util.LOG('Looking for server: {0}'.format(search))
    for server in resources:
        if search == server.name.lower():
            util.LOG('Server found: {0}'.format(server))
            return server
    util.LOG('Unable to find server: {0}'.format(search))
    raise exceptions.NotFound('Unable to find server: {0}'.format(search))


def findResourceByID(resources, ID):
    """ Searches server.clientIdentifier """
    util.LOG('Looking for server by ID: {0}'.format(ID))
    for server in resources:
        if ID == server.clientIdentifier:
            util.LOG('Server found by ID: {0}'.format(server))
            return server
    util.LOG('Unable to find server by ID: {0}'.format(ID))
    raise exceptions.NotFound('Unable to find server by ID: {0}'.format(ID))
