from datetime import datetime

import exceptions
import util

# Search Types - Plex uses these to filter specific media types when searching.
SEARCHTYPES = {
    'movie': 1,
    'show': 2,
    'season': 3,
    'episode': 4,
    'artist': 8,
    'album': 9,
    'track': 10
}

LIBRARY_TYPES = {}


def registerLibType(cls):
    LIBRARY_TYPES[cls.TYPE] = cls
    return cls


class PlexValue(unicode):
    def __new__(cls, value, parent=None):
        self = super(PlexValue, cls).__new__(cls, value)
        self.parent = parent
        self.NA = False
        return self

    def asBool(self):
        return self == '1'

    def asInt(self):
        return int(self)

    def asFloat(self):
        return float(self)

    def asDatetime(self):
        if self.isdigit():
            return datetime.fromtimestamp(int(self))
        else:
            return datetime.strptime(self, '%Y-%m-%d')

    def asURL(self):
        return self.parent.server.url(self)

    def asTranscodedImageURL(self, w, h):
        return self.parent.server.transcodedImageURL(self, w, h)


class PlexItemList(object):
    def __init__(self, data, item_cls, tag, server=None):
        self._data = data
        self._itemClass = item_cls
        self._itemTag = tag
        self._server = server
        self._items = None

    @property
    def items(self):
        if self._items is None:
            if self._server:
                self._items = [self._itemClass(elem, server=self._server) for elem in self._data if elem.tag == self._itemTag]
            else:
                self._items = [self._itemClass(elem) for elem in self._data if elem.tag == self._itemTag]

        return self._items

    def __call__(self):
        return self.items


class PlexMediaItemList(PlexItemList):
    def __init__(self, data, item_cls, tag, initpath=None, server=None, media=None):
        self._data = data
        self._itemClass = item_cls
        self._itemTag = tag
        self._initpath = initpath
        self._server = server
        self._media = media
        self._items = None

    @property
    def items(self):
        if self._items is None:
            self._items = [self._itemClass(elem, self._initpath, self._server, self._media) for elem in self._data if elem.tag == self._itemTag]

        return self._items


class PlexObject(object):
    def __init__(self, data, initpath=None, server=None):
        self.initpath = initpath
        self.key = None
        self.server = server

        if data is None:
            return

        self._setData(data)

        print '{0} {0}'.format(self.initpath, self.key)

        self.init(data)

    def _setData(self, data):
        for k, v in data.attrib.items():
            setattr(self, k, PlexValue(v, self))

    def __getattr__(self, attr):
        if not self.isFullObject():
            self.reload()
            if attr in self.__dict__:
                return self.__dict__[attr]

        a = PlexValue('')
        a.NA = True

        try:
            setattr(self, attr, a)
        except AttributeError:
            util.LOG('Failed to set attribute: {0} ({1})'.format(attr, self.__class__))

        return a

    def init(self, data):
        pass

    def isFullObject(self):
        return self.initpath is None or self.key is None or self.initpath == self.key

    def refresh(self):
        import requests
        self.server.query('%s/refresh' % self.key, method=requests.put)

    def reload(self):
        """ Reload the data for this object from PlexServer XML. """
        data = self.server.query(self.key)
        self.initpath = self.key
        self._setData(data[0])

    def _findLocation(self, data):
        elem = data.find('Location')
        if elem is not None:
            return elem.attrib.get('path')
        return None

    def _findPlayer(self, data):
        elem = data.find('Player')
        if elem is not None:
            from plexapi.client import Client
            return Client(self.server, elem)
        return None

    def _findStreams(self, streamtype):
        streams = []
        for media in self.media():
            for part in media.parts:
                for stream in part.streams:
                    if stream.TYPE == streamtype:
                        streams.append(stream)
        return streams

    def _findTranscodeSession(self, data):
        elem = data.find('TranscodeSession')
        if elem is not None:
            from plexapi import media
            return media.TranscodeSession(self.server, elem)
        return None

    def _findUser(self, data):
        elem = data.find('User')
        if elem is not None:
            from plexapi.myplex import MyPlexUser
            return MyPlexUser(elem, self.initpath)
        return None


def findItem(server, path, title):
    for elem in server.query(path):
        if elem.attrib.get('title').lower() == title.lower():
            return buildItem(server, elem, path)
    raise exceptions.NotFound('Unable to find item: {0}'.format(title))


def buildItem(server, elem, initpath, bytag=False):
    libtype = elem.tag if bytag else elem.attrib.get('type')
    if libtype in LIBRARY_TYPES:
        cls = LIBRARY_TYPES[libtype]
        return cls(elem, initpath=initpath, server=server)
    raise exceptions.UnknownType('Unknown library type: {0}'.format(libtype))


def listItems(server, path, libtype=None, watched=None, bytag=False):
    items = []
    for elem in server.query(path):
        if libtype and elem.attrib.get('type') != libtype:
            continue
        if watched is True and elem.attrib.get('viewCount', 0) == 0:
            continue
        if watched is False and elem.attrib.get('viewCount', 0) >= 1:
            continue
        try:
            items.append(buildItem(server, elem, path, bytag))
        except exceptions.UnknownType:
            pass
    return items


def searchType(libtype):
    searchtypesstrs = [str(k) for k in SEARCHTYPES.keys()]
    if libtype in SEARCHTYPES + searchtypesstrs:
        return libtype
    stype = SEARCHTYPES.get(libtype.lower())
    if not stype:
        raise exceptions.NotFound('Unknown libtype: %s' % libtype)
    return stype
