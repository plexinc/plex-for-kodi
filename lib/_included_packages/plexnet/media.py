import plexobjects
import plexstream
import util


class MediaItem(plexobjects.PlexObject):
    def isLibraryItem(self):
        return True

    def isVideoItem(self):
        return False

    def isOnlineItem(self):
        return self.isChannelItem() or self.isMyPlexItem() or self.isVevoItem() or self.isIvaItem()

    def isMyPlexItem(self):
        return self.container.server.TYPE == 'MYPLEXSERVER' or self.container.identifier == 'com.plexapp.plugins.myplex'

    def isChannelItem(self):
        identifier = self.getIdentifier() or "com.plexapp.plugins.library"
        return not self.isLibraryItem() and not self.isMyPlexItem() and identifier != "com.plexapp.plugins.library"

    def isVevoItem(self):
        return 'vevo://' in self.guid

    def isIvaItem(self):
        return 'iva://' in self.guid

    def sIPhoto(self):
        return (self.title == "iPhoto" or self.container.title == "iPhoto" or (self.mediaType == "Image" or self.mediaType == "Movie"))

    def getIdentifier(self):
        identifier = self.identifier

        if identifier is None:
            identifier = self.container.identifier

        # HACK
        # PMS doesn't return an identifier for playlist items. If we haven't found
        # an identifier and the key looks like a library item, then we pretend like
        # the identifier was set.
        #
        if identifier is None:  # Modified from Roku code which had no check for None with iPhoto - is that right?
            if self.key.startswith('/library/metadata'):
                identifier = "com.plexapp.plugins.library"
            elif self.isIPhoto():
                identifier = "com.plexapp.plugins.iphoto"

        return identifier

    def getQualityType(self, server=None):
        if self.isOnlineItem():
            return util.QUALITY_ONLINE

        if not server:
            server = self.getServer()

        return server.isLocalConnection() and util.QUALITY_LOCAL or util.QUALITY_REMOTE


class Media(plexobjects.PlexObject):
    TYPE = 'Media'

    def __init__(self, data, initpath=None, server=None, video=None):
        plexobjects.PlexObject.__init__(self, data, initpath=initpath, server=server)
        self.video = video
        self.parts = [MediaPart(elem, initpath=self.initpath, server=self.server, media=self) for elem in data]

    def __repr__(self):
        title = self.video.title.replace(' ', '.')[0:20]
        return '<%s:%s>' % (self.__class__.__name__, title.encode('utf8'))


class MediaPart(plexobjects.PlexObject):
    TYPE = 'Part'

    def __init__(self, data, initpath=None, server=None, media=None):
        plexobjects.PlexObject.__init__(self, data, initpath=initpath, server=server)
        self.media = media
        self.streams = [MediaPartStream.parse(e, initpath=self.initpath, server=server, part=self) for e in data if e.tag == 'Stream']

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.id)

    def selectedStream(self, stream_type):
        streams = filter(lambda x: stream_type == x.type, self.streams)
        selected = list(filter(lambda x: x.selected is True, streams))
        if len(selected) == 0:
            return None
        return selected[0]


class MediaPartStream(plexstream.PlexStream):
    TYPE = None
    STREAMTYPE = None

    def __init__(self, data, initpath=None, server=None, part=None):
        plexobjects.PlexObject.__init__(self, data, initpath, server)
        self.part = part

    @staticmethod
    def parse(data, initpath=None, server=None, part=None):
        STREAMCLS = {
            1: VideoStream,
            2: AudioStream,
            3: SubtitleStream
        }
        stype = int(data.attrib.get('streamType'))
        cls = STREAMCLS.get(stype, MediaPartStream)
        return cls(data, initpath=initpath, server=server, part=part)

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.id)


class VideoStream(MediaPartStream):
    TYPE = 'videostream'
    STREAMTYPE = plexstream.PlexStream.TYPE_VIDEO


class AudioStream(MediaPartStream):
    TYPE = 'audiostream'
    STREAMTYPE = plexstream.PlexStream.TYPE_AUDIO


class SubtitleStream(MediaPartStream):
    TYPE = 'subtitlestream'
    STREAMTYPE = plexstream.PlexStream.TYPE_SUBTITLE


class TranscodeSession(plexobjects.PlexObject):
    TYPE = 'TranscodeSession'


class MediaTag(plexobjects.PlexObject):
    TYPE = None

    def __repr__(self):
        tag = self.tag.replace(' ', '.')[0:20]
        return '<%s:%s:%s>' % (self.__class__.__name__, self.id, tag)


class Collection(MediaTag):
    TYPE = 'Collection'
    FILTER = 'collection'


class Country(MediaTag):
    TYPE = 'Country'
    FILTER = 'country'


class Director(MediaTag):
    TYPE = 'Director'
    FILTER = 'director'


class Genre(MediaTag):
    TYPE = 'Genre'
    FILTER = 'genre'


class Mood(MediaTag):
    TYPE = 'Mood'
    FILTER = 'mood'


class Producer(MediaTag):
    TYPE = 'Producer'
    FILTER = 'producer'


class Role(MediaTag):
    TYPE = 'Role'
    FILTER = 'role'


class Similar(MediaTag):
    TYPE = 'Similar'
    FILTER = 'similar'


class Writer(MediaTag):
    TYPE = 'Writer'
    FILTER = 'writer'
