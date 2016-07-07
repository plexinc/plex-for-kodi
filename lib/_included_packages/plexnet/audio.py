# -*- coding: utf-8 -*-
import plexobjects
import plexmedia
import media


class Audio(media.MediaItem):
    def _setData(self, data):
        for k, v in data.attrib.items():
            setattr(self, k, plexobjects.PlexValue(v, self))

        self.key = plexobjects.PlexValue(self.key.replace('/children', ''), self)

    def isMusicItem(self):
        return True


@plexobjects.registerLibType
class Artist(Audio):
    TYPE = 'artist'

    def _setData(self, data):
        Audio._setData(self, data)
        if self.isFullObject():
            self.countries = plexobjects.PlexItemList(data, media.Country, media.Country.TYPE, server=self.server)
            self.genres = plexobjects.PlexItemList(data, media.Genre, media.Genre.TYPE, server=self.server)
            self.similar = plexobjects.PlexItemList(data, media.Similar, media.Similar.TYPE, server=self.server)

    def albums(self):
        path = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.listItems(self.server, path, Album.TYPE)

    def album(self, title):
        path = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def tracks(self, watched=None):
        leavesKey = '/library/metadata/%s/allLeaves' % self.ratingKey
        return plexobjects.listItems(self.server, leavesKey, watched=watched)

    def track(self, title):
        path = '/library/metadata/%s/allLeaves' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def get(self, title):
        return self.track(title)

    def isFullObject(self):
        # plex bug? http://bit.ly/1Sc2J3V
        fixed_key = self.key.replace('/children', '')
        return self.initpath == fixed_key

    def refresh(self):
        self.server.query('/library/metadata/%s/refresh' % self.ratingKey)


@plexobjects.registerLibType
class Album(Audio):
    TYPE = 'album'

    def _setData(self, data):
        Audio._setData(self, data)
        if self.isFullObject():
            self.genres = plexobjects.PlexItemList(data, media.Genre, media.Genre.TYPE, server=self.server)

    def tracks(self, watched=None):
        childrenKey = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.listItems(self.server, childrenKey, watched=watched)

    def track(self, title):
        path = '/library/metadata/%s/children' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def get(self, title):
        return self.track(title)

    def isFullObject(self):
        # plex bug? http://bit.ly/1Sc2J3V
        fixed_key = self.key.replace('/children', '')
        return self.initpath == fixed_key

    def artist(self):
        return plexobjects.listItems(self.server, self.parentKey)[0]

    def watched(self):
        return self.tracks(watched=True)

    def unwatched(self):
        return self.tracks(watched=False)


@plexobjects.registerLibType
class Track(Audio):
    TYPE = 'track'

    def _setData(self, data):
        Audio._setData(self, data)
        if self.isFullObject():
            self.moods = plexobjects.PlexItemList(data, media.Mood, media.Mood.TYPE, server=self.server)
            self.media = plexobjects.PlexMediaItemList(data, plexmedia.PlexMedia, media.Media.TYPE, initpath=self.initpath, server=self.server, media=self)

        # data for active sessions
        self.user = self._findUser(data)
        self.player = self._findPlayer(data)
        self.transcodeSession = self._findTranscodeSession(data)

    @property
    def settings(self):
        if not self._settings:
            import plexapp
            self._settings = plexapp.PlayerSettingsInterface()

        return self._settings

    @property
    def thumbUrl(self):
        return self.server.url(self.parentThumb)

    def transcodedThumbURL(self, w=400, h=400):
        return self.server.getImageTranscodeURL(self.parentThumb, w, h)

    def album(self):
        return plexobjects.listItems(self.server, self.parentKey)[0]

    def artist(self):
        return plexobjects.listItems(self.server, self.grandparentKey)[0]

    def getStreamURL(self, **params):
        return self._getStreamURL(**params)
