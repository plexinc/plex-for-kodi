# -*- coding: utf-8 -*-
"""
PlexPhoto
"""
from plexapi import utils
NA = utils.NA


@utils.register_libtype
class Photo(utils.PlexPartialObject):
    TYPE = 'photo'

    def _loadData(self, data):
        self.addedAt = utils.toDatetime(data.attrib.get('addedAt', NA))
        self.key = data.attrib.get('key', NA)
        self.ratingKey = data.attrib.get('ratingKey', NA)
        self.summary = data.attrib.get('summary', NA)
        self.thumb = data.attrib.get('thumb', NA)
        self.title = data.attrib.get('title', NA)
        self.type = data.attrib.get('type', NA)
        self.updatedAt = utils.toDatetime(data.attrib.get('updatedAt', NA))
        self.index = utils.cast(int, data.attrib.get('index', NA))
        self.parentKey = data.attrib.get('ratingKey', NA)
        self.parentRatingKey = data.attrib.get('parentRatingKey', NA)
        self.ratingKey = data.attrib.get('ratingKey', NA)
        self.year = utils.cast(int, data.attrib.get('year', NA))
        self.originallyAvailableAt = utils.toDatetime(data.attrib.get('originallyAvailableAt', NA), '%Y-%m-%d')
        self.createdAtTZOffset = utils.cast(int, data.attrib.get('createdAtTZOffset', NA))
        self.device = data.attrib.get('device', NA)
        self.filename = data.attrib.get('filename', NA)
        self.createdAtAccuracy = data.attrib.get('createdAtAccuracy', NA)

    def analyze(self):
        """ The primary purpose of media analysis is to gather information about that media
            item. All of the media you add to a Library has properties that are useful to
            know–whether it's a video file, a music track, or one of your photos.
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

    def play(self, client):
        client.playMedia(self)

    def refresh(self):
        self.server.query('%s/refresh' % self.key, method=self.server.session.put)
