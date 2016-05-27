import plexobjects


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


class MediaPartStream(plexobjects.PlexObject):
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
    STREAMTYPE = 1


class AudioStream(MediaPartStream):
    TYPE = 'audiostream'
    STREAMTYPE = 2


class SubtitleStream(MediaPartStream):
    TYPE = 'subtitlestream'
    STREAMTYPE = 3


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
