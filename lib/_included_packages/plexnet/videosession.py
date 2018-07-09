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


class VideoSessionInfo:
    currentSessionMediaPart = None
    currentMediaPart = None
    currentSessionMedia = None
    currentMedia = None

    def __init__(self, video_session, media_item):
        self.mediaItem = media_item
        self.session = video_session
        self.findMediaParts(self.session.media, self.mediaItem.media)
        self.attributes = SessionAttributes()

        self.fillData()

    def findMediaParts(self, session_media, orig_media):
        for media in session_media:
            for part in media.parts:
                if part.selected:
                    self.currentSessionMediaPart = part
                    self.currentSessionMedia = media
                    break

        for media in orig_media:
            for part in media.parts:
                if self.currentSessionMediaPart and part.id == self.currentSessionMediaPart.id:
                    self.currentMediaPart = part
                    self.currentMedia = media
                    break

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
        data = [self.currentSessionMediaPart.decision]
        # if self.session.transcodeSession:
        #     if self.session.transcodeSession.context:
        #         data.append(self.session.transcodeSession.context)

        if self.session.player.local:
            data.append("local")

        self.attributes.add("Mode", *data)

    def fillContainerInfo(self):
        data = []
        if self.currentMediaPart.attrib_container != self.currentSessionMediaPart.attrib_container:
            data.append("%s->%s" % (self.currentMediaPart.attrib_container, self.currentSessionMediaPart.attrib_container))
        else:
            data.append(self.currentMediaPart.attrib_container)

        self.attributes.add("Container", *data)

    def fillVideoInfo(self):
        data = []
        currentSessionStream = None
        for stream in self.currentSessionMediaPart.streams:
            if stream.streamType == "1" and (stream.selected == "1" or (stream.default == "1" and not currentSessionStream)):
                currentSessionStream = stream
                # don't break the loop here as we might have multiple video streams

        currentStream = None
        if currentSessionStream:
            for stream in self.currentMediaPart.streams:
                if stream.id == currentSessionStream.id:
                    currentStream = stream
                    break

        if not currentStream:
            return

        if self.currentMedia.videoResolution != self.currentSessionMedia.videoResolution:
            data.append("%s->%s" % (self.normRes(self.currentMedia.videoResolution), self.normRes(self.currentSessionMedia.videoResolution)))
        else:
            data.append(self.normRes(self.currentMedia.videoResolution))

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
        currentSessionStream = None
        for stream in self.currentSessionMediaPart.streams:
            if stream.streamType == "2" and stream.selected == "1":
                currentSessionStream = stream
                break

        currentStream = None
        if currentSessionStream:
            for stream in self.currentMediaPart.streams:
                if stream.id == currentSessionStream.id:
                    currentStream = stream
                    break

        if not currentStream:
            return

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
        currentSessionStream = None
        for stream in self.currentSessionMediaPart.streams:
            if stream.streamType == "3" and stream.selected == "1":
                currentSessionStream = stream
                break

        currentStream = None
        if currentSessionStream:
            for stream in self.currentMediaPart.streams:
                if stream.id == currentSessionStream.id:
                    currentStream = stream
                    break

        if not currentStream:
            return

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
        self.attributes.add("User", *["%s @ %s" % (self.session.user.title, self.mediaItem.server.name)])
