import plexobjects
import media


class Video(plexobjects.PlexObject):
    TYPE = None

    def analyze(self):
        """ The primary purpose of media analysis is to gather information about that media
            item. All of the media you add to a Library has properties that are useful to
            know - whether it's a video file, a music track, or one of your photos.
        """
        self.server.query('/%s/analyze' % self.key)

    def markWatched(self):
        path = '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self.server.query(path)
        self.reload()

    def markUnwatched(self):
        path = '/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self.server.query(path)
        self.reload()

    # def play(self, client):
    #     client.playMedia(self)

    def refresh(self):
        self.server.query('%s/refresh' % self.key, method=self.server.session.put)


@plexobjects.registerLibType
class Movie(Video):
    TYPE = 'movie'

    def _setData(self, data):
        Video._setData(self, data)
        if self.isFullObject():
            self.collections = plexobjects.PlexItemList(data, media.Collection, media.Collection.TYPE, server=self.server)
            self.countries = plexobjects.PlexItemList(data, media.Country, media.Country.TYPE, server=self.server)
            self.directors = plexobjects.PlexItemList(data, media.Director, media.Director.TYPE, server=self.server)
            self.genres = plexobjects.PlexItemList(data, media.Genre, media.Genre.TYPE, server=self.server)
            self.media = plexobjects.PlexMediaItemList(data, media.Media, media.Media.TYPE, initpath=self.initpath, server=self.server, media=self)
            self.producers = plexobjects.PlexItemList(data, media.Producer, media.Producer.TYPE, server=self.server)
            self.roles = plexobjects.PlexItemList(data, media.Role, media.Role.TYPE, server=self.server)
            self.writers = plexobjects.PlexItemList(data, media.Writer, media.Writer.TYPE, server=self.server)

        self._videoStreams = None
        self._audioStreams = None
        self._subtitleStreams = None

        # data for active sessions
        self.sessionKey = plexobjects.PlexValue(data.attrib.get('sessionKey', ''), self)
        self.user = self._findUser(data)
        self.player = self._findPlayer(data)
        self.transcodeSession = self._findTranscodeSession(data)

    @property
    def videoStreams(self):
        if self._videoStreams is None:
            self._videoStreams = self._findStreams('videostream')
        return self._videoStreams

    @property
    def audioStreams(self):
        if self._audioStreams is None:
            self._audioStreams = self._findStreams('audiostream')
        return self._audioStreams

    @property
    def subtitleStreams(self):
        if self._subtitleStreams is None:
            self._subtitleStreams = self._findStreams('subtitlestream')
        return self._subtitleStreams

    @property
    def actors(self):
        return self.roles

    @property
    def isWatched(self):
        return self.viewCount > 0

    def getStreamURL(self, **params):
        return self._getStreamURL(**params)


@plexobjects.registerLibType
class Show(Video):
    TYPE = 'show'

    def _setData(self, data):
        Video._setData(self, data)
        if self.isFullObject():
            self.genres = plexobjects.PlexItemList(data, media.Genre, media.Genre.TYPE, server=self.server)
            self.roles = plexobjects.PlexItemList(data, media.Role, media.Role.TYPE, server=self.server)

    @property
    def isWatched(self):
        return self.viewedLeafCount == self.leafCount

    def seasons(self):
        path = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.listItems(self.server, path, Season.TYPE)

    def season(self, title):
        path = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def episodes(self, watched=None):
        leavesKey = '/library/metadata/%s/allLeaves' % self.ratingKey
        return plexobjects.listItems(self.server, leavesKey, watched=watched)

    def episode(self, title):
        path = '/library/metadata/%s/allLeaves' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def watched(self):
        return self.episodes(watched=True)

    def unwatched(self):
        return self.episodes(watched=False)

    def get(self, title):
        return self.episode(title)

    def refresh(self):
        self.server.query('/library/metadata/%s/refresh' % self.ratingKey)


@plexobjects.registerLibType
class Season(Video):
    TYPE = 'season'

    @property
    def isWatched(self):
        return self.viewedLeafCount == self.leafCount

    def episodes(self, watched=None):
        childrenKey = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.listItems(self.server, childrenKey, watched=watched)

    def episode(self, title):
        path = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def get(self, title):
        return self.episode(title)

    def show(self):
        return plexobjects.listItems(self.server, self.parentKey)[0]

    def watched(self):
        return self.episodes(watched=True)

    def unwatched(self):
        return self.episodes(watched=False)


@plexobjects.registerLibType
class Episode(Video):
    TYPE = 'episode'

    def _setData(self, data):
        Video._setData(self, data)
        if self.isFullObject():
            self.directors = plexobjects.PlexItemList(data, media.Director, media.Director.TYPE, server=self.server)
            self.media = plexobjects.PlexMediaItemList(data, media.Media, media.Media.TYPE, initpath=self.initpath, server=self.server, media=self)
            self.writers = plexobjects.PlexItemList(data, media.Writer, media.Writer.TYPE, server=self.server)

        self._videoStreams = None
        self._audioStreams = None
        self._subtitleStreams = None

        # data for active sessions
        self.sessionKey = plexobjects.PlexValue(data.attrib.get('sessionKey', ''), self)
        self.user = self._findUser(data)
        self.player = self._findPlayer(data)
        self.transcodeSession = self._findTranscodeSession(data)

    @property
    def defaultThumb(self):
        return self.grandparentThumb or self.parentThumb or self.thumb

    @property
    def videoStreams(self):
        if self._videoStreams is None:
            self._videoStreams = self._findStreams('videostream')
        return self._videoStreams

    @property
    def audioStreams(self):
        if self._audioStreams is None:
            self._audioStreams = self._findStreams('audiostream')
        return self._audioStreams

    @property
    def subtitleStreams(self):
        if self._subtitleStreams is None:
            self._subtitleStreams = self._findStreams('subtitlestream')
        return self._subtitleStreams

    @property
    def isWatched(self):
        return self.viewCount > 0

    def getStreamURL(self, **params):
        return self._getStreamURL(videoResolution='800x600', **params)

    def season(self):
        return plexobjects.listItems(self.server, self.parentKey)[0]

    def show(self):
        return plexobjects.listItems(self.server, self.grandparentKey)[0]


@plexobjects.registerLibType
class Clip(Video):
    TYPE = 'clip'

    @property
    def isWatched(self):
        return self.viewCount > 0

    def getStreamURL(self, **params):
        return self._getStreamURL(videoResolution='800x600', **params)
