# coding=utf-8

from collections import OrderedDict

import util


class SessionAttribute:
    name = None
    data = None

    def __init__(self, name, *data):
        self.name = name
        self.data = data

    @property
    def label(self):
        return self.name

    @property
    def value(self):
        return ", ".join(self.data)

    def __str__(self):
        return "%s: %s" % (self.label, self.value)

    def __repr__(self):
        return str(self)


class SessionAttributes(OrderedDict):
    def add(self, name, *data):
        self[name] = SessionAttribute(name, *data)


class MediaDetails:
    details = None

    def __init__(self, mediaContainer, by_ref=None):
        self.details = self.findMediaDetails(mediaContainer, by_ref=by_ref)

    def findMediaDetails(self, mediaList, by_ref=None):
        """

        :type by_ref: reference MediaDetails object
        """
        data = {
            "media": None,
            "part": None,
            "video_stream": None,
            "audio_stream": None,
            "subtitle_stream": None
        }

        for media in mediaList:
            for part in media.parts:
                if not by_ref:
                    if part.selected:
                        data["part"] = part
                        data["media"] = media

                        for stream in part.streams:
                            if stream.streamType == "1" and (
                                    stream.selected == "1" or (
                                    stream.default == "1" and not data["video_stream"])):
                                data["video_stream"] = stream

                            elif stream.streamType == "2" and stream.selected == "1":
                                data["audio_stream"] = stream

                            elif stream.streamType == "3" and stream.selected == "1":
                                data["subtitle_stream"] = stream

                        break
                else:
                    if part.id == by_ref.part.id:
                        data["part"] = part
                        data["media"] = media

                        for stream in part.streams:
                            if stream.id == by_ref.video_stream.id:
                                data["video_stream"] = stream

                            elif stream.id == by_ref.audio_stream.id:
                                data["audio_stream"] = stream

                            elif stream.id == by_ref.subtitle_stream.id:
                                data["subtitle_stream"] = stream
                        break

        return data

    def __getattr__(self, item):
        if self.details and item in self.details:
            return self.details[item]
        raise AttributeError("%r object has no attribute %r" % (self.__class__, item))


class MediaDetailsHolder:
    session = None
    original = None

    def __init__(self, originalMedia, sessionMedia):
        self.session = MediaDetails(sessionMedia)
        self.original = MediaDetails(originalMedia, by_ref=self.session)


class VideoSessionInfo:
    def __init__(self, sessionMediaContainer, mediaContainer):
        self.mediaItem = mediaContainer
        self.session = sessionMediaContainer
        self.details = MediaDetailsHolder(self.mediaItem.media, self.session.media)
        self.attributes = SessionAttributes()

        self.fillData()

    def fillData(self):
        # fill info
        self.fillModeInfo()
        self.fillContainerInfo()
        self.fillVideoInfo()
        self.fillAudioInfo()
        self.fillSubtitleInfo()
        self.fillServerInfo()

    def normRes(self, res):
        try:
            int(res)
        except:
            pass
        else:
            res += "p"
        return res

    def fillModeInfo(self):
        data = [self.details.session.part.decision]
        # if self.session.transcodeSession:
        #     if self.session.transcodeSession.context:
        #         data.append(self.session.transcodeSession.context)

        if self.session.player.local:
            data.append("local")

        self.attributes.add("Mode", *data)

    def fillContainerInfo(self):
        data = []
        if self.details.original.part.attrib_container != self.details.session.part.attrib_container:
            data.append("%s->%s" % (self.details.original.part.attrib_container, self.details.session.part.attrib_container))
        else:
            data.append(self.details.original.part.attrib_container)

        self.attributes.add("Container", *data)

    def fillVideoInfo(self):
        data = []

        if not self.details.original.video_stream:
            return

        currentMedia = self.details.original.media
        currentSessionMedia = self.details.session.media
        currentStream = self.details.original.video_stream
        currentSessionStream = self.details.session.video_stream

        if currentMedia.videoResolution != currentSessionMedia.videoResolution:
            data.append("%s->%s" % (self.normRes(currentMedia.videoResolution), self.normRes(currentSessionMedia.videoResolution)))
        else:
            data.append(self.normRes(currentMedia.videoResolution))

        if currentStream.bitrate != currentSessionStream.bitrate:
            data.append("%s->%s" % (currentStream.bitrate, currentSessionStream.bitrate + "kbit"))
        else:
            data.append(currentStream.bitrate + "kbit")

        if currentSessionStream.decision:
            decision = currentSessionStream.decision
            if self.session.transcodeSession.videoDecision == "transcode" and self.session.transcodeSession.transcodeHwEncoding:
                decision += " HW"

            data.append(decision)

        # if currentSessionVideoStream.location:
        #     data.append(currentSessionVideoStream.location)

        self.attributes.add("Video", *data)

    def fillAudioInfo(self):
        data = []

        if not self.details.original.audio_stream:
            return

        currentStream = self.details.original.audio_stream
        currentSessionStream = self.details.session.audio_stream

        if currentStream.codec != currentSessionStream.codec:
            data.append("%s->%s" % (currentStream.codec, currentSessionStream.codec))
        else:
            data.append(currentStream.codec)

        if currentStream.bitrate != currentSessionStream.bitrate:
            data.append("%s->%s" % (currentStream.bitrate, currentSessionStream.bitrate + "kbit"))
        else:
            data.append(currentStream.bitrate + "kbit")

        if currentStream.channels != currentSessionStream.channels:
            data.append("%s->%s" % (currentStream.channels, currentSessionStream.channels + "ch"))
        else:
            data.append(currentStream.channels + "ch")

        if currentSessionStream.decision:
            data.append(currentSessionStream.decision)

        # if currentSessionStream.location:
        #     data.append(currentSessionStream.location)

        self.attributes.add("Audio", *data)

    def fillSubtitleInfo(self):
        data = []
        if not self.details.original.audio_stream:
            return

        currentStream = self.details.original.subtitle_stream
        currentSessionStream = self.details.session.subtitle_stream

        if currentStream.codec != currentSessionStream.codec:
            codec = "burn" if currentSessionStream.burn else currentSessionStream.codec
            data.append("%s->%s" % (currentStream.codec, codec))
        else:
            data.append(currentStream.codec)

        if currentSessionStream.decision and currentSessionStream.decision != "burn":
            data.append(currentSessionStream.decision)

        if currentSessionStream.location:
            data.append(currentSessionStream.location)

        self.attributes.add("Subtitles", *data)

    def fillServerInfo(self):
        self.attributes.add("User", *[u"%s @ %s" % (self.session.user.title, self.mediaItem.server.name)])
