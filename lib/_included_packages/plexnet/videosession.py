# coding=utf-8
from collections import OrderedDict

import util
from plexnet.plexobjects import listItems
from plexnet import plexapp


class MediaDetails:
    details = None

    def __init__(self, mediaContainer, mediaChoice):
        self.details = self.findMediaDetails(mediaContainer, mediaChoice)

    def findMediaDetails(self, mediaList, mediaChoice):
        """

        :type byRef: reference MediaDetails object
        """
        data = {
            "media": None,
            "part": None,
            "video_stream": None,
            "audio_stream": None,
            "subtitle_stream": None
        }

        # we can't use mediaChoice here, directly, because it's the original mediaItems' mediaChoice in case of
        # incomplete data
        for media in mediaList.media:
            if media.id == mediaChoice.media.id:
                data["media"] = media

                for part in media.parts:
                    if part.id == mediaChoice.part.id:
                        data["part"] = part

                        for stream in part.streams:
                            if stream.id == mediaChoice.videoStream.id:
                                data["video_stream"] = stream
                            elif stream.id == mediaChoice.audioStream.id:
                                data["audio_stream"] = stream
                            elif stream.id == mediaChoice.subtitleStream.id:
                                data["subtitle_stream"] = stream
        return data

    def __getattr__(self, item):
        if self.details and item in self.details:
            return self.details[item]
        raise AttributeError("%r object has no attribute %r" % (self.__class__, item))

    def incompleteSessionDataToMedia(self, data, media):
        """
        updates mediaItem with timeline response bandwidth/transcodeSession data
        :param data:
        :param media:
        :return:
        """
        decision = "directplay"

        media.bandwidths = media._findBandwidths(data)
        media.transcodeSession = media._findTranscodeSession(data)

        if media.transcodeSession:
            decision = "transcode"

            # fill remaining data
            self.part.attrib_container = media.transcodeSession.attrib_container

            for bw in media.bandwidths:
                if bw.resolution:
                    self.media.videoResolution = bw.resolution
                    break

            if self.video_stream:
                # sadly we don't know the final bitrate for the video/audio streams with incomplete data
                self.video_stream.bitrate = "?"
                self.video_stream.decision = media.transcodeSession.videoDecision
                self.video_stream.codec = media.transcodeSession.videoCodec

            if self.audio_stream:
                self.audio_stream.decision = media.transcodeSession.audioDecision
                self.audio_stream.codec = media.transcodeSession.audioCodec
                self.audio_stream.channels = media.transcodeSession.audioChannels
                self.audio_stream.bitrate = "?"

            if self.subtitle_stream:
                self.subtitle_stream.decision = media.transcodeSession.subtitleDecision
                if self.subtitle_stream.decision == "burn":
                    self.subtitle_stream.burn = True
                    self.subtitle_stream.codec = "burn"

        self.part.decision = decision


class MediaDetailsHolder:
    session = None
    original = None

    def __init__(self, originalMedia, sessionMedia, mediaChoice):
        self.session = MediaDetails(sessionMedia, mediaChoice)
        self.original = MediaDetails(originalMedia, mediaChoice)


ATTRIBUTE_TYPES = OrderedDict()


def registerAttributeType(cls):
    ATTRIBUTE_TYPES[cls.name] = cls
    return cls


def dpConditionMet(condition, resultTrue, resultFalse=None):
    """

    :rtype: list
    """
    return [resultTrue] if condition and resultTrue else [resultFalse] if resultFalse else []


def dpAttributeIfExists(ref, attrib, returnValue=None):
    """

    :rtype: list
    """
    result = getattr(ref, attrib, None)
    if returnValue and result:
        return [returnValue]

    return [result] if result else []


def dpAttributeDifferenceDefault(ref1, ref2, attribute, formatTrue=u"%(val1)s->%(val2)s", formatFalse=u"%(val1)s",
                                 valueFormatter=lambda v1, v2: [v1, v2]):
    """

    :rtype: string
    """
    val1 = getattr(ref1, attribute, None)
    val2 = getattr(ref2, attribute, None)
    formatted_val1, formatted_val2 = valueFormatter(val1, val2)

    if val1 != val2:
        return formatTrue % {"val1": formatted_val1, "val2": formatted_val2}
    return (formatFalse % {"val1": formatted_val1, "val2": formatted_val2}) if formatFalse else formatted_val1


class SessionAttribute:
    name = None
    data = None
    displayCondition = None
    dataPoints = []

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


@registerAttributeType
class ModeAttribute(SessionAttribute):
    name = "Mode"
    dataPoints = [
        lambda i: [
            i.details.session.part.decision,
        ],
        lambda i: dpAttributeIfExists(i.session.player, "local", returnValue="local")
    ]


@registerAttributeType
class ContainerAttribute(SessionAttribute):
    name = "Container"
    dataPoints = [
        lambda i: [
            dpAttributeDifferenceDefault(i.details.original.part, i.details.session.part, "attrib_container"),
        ]
    ]


@registerAttributeType
class VideoAttribute(SessionAttribute):
    name = "Video"
    displayCondition = staticmethod(lambda i: bool(i.details.original.video_stream))
    dataPoints = [
        lambda i: [
            dpAttributeDifferenceDefault(i.details.original.media, i.details.session.media, "videoResolution",
                                         valueFormatter=lambda v1, v2: [i.normRes(v1), i.normRes(v2)]),
            dpAttributeDifferenceDefault(i.details.original.video_stream, i.details.session.video_stream, "bitrate",
                                         u"%(val1)s->%(val2)skbit", u"%(val1)skbit"),

        ],
        lambda i: [
            (i.details.session.video_stream.decision + " HW")
            if i.session.transcodeSession.videoDecision == "transcode" and i.session.transcodeSession.transcodeHwEncoding
            else i.details.session.video_stream.decision
        ]
    ]


@registerAttributeType
class AudioAttribute(SessionAttribute):
    name = "Audio"
    displayCondition = staticmethod(lambda i: bool(i.details.original.audio_stream))
    dataPoints = [
        lambda i: [
            dpAttributeDifferenceDefault(i.details.original.audio_stream, i.details.session.audio_stream, "codec"),
            dpAttributeDifferenceDefault(i.details.original.audio_stream, i.details.session.audio_stream, "bitrate",
                                         u"%(val1)s->%(val2)skbit", u"%(val1)skbit"),
            dpAttributeDifferenceDefault(i.details.original.audio_stream, i.details.session.audio_stream, "channels",
                                         u"%(val1)s->%(val2)sch", u"%(val1)sch"),
        ],
        lambda i: dpAttributeIfExists(i.details.session.audio_stream, "decision")
    ]


@registerAttributeType
class SubtitlesAttribute(SessionAttribute):
    name = "Subtitles"
    displayCondition = staticmethod(lambda i: bool(i.details.original.subtitle_stream))
    dataPoints = [
        lambda i: [
            dpAttributeDifferenceDefault(i.details.original.subtitle_stream, i.details.session.subtitle_stream, "codec",
                                         valueFormatter=lambda v1, v2: [v1,
                                                                        "burn" if i.details.session.subtitle_stream.burn else v2]),
        ],
        lambda i: dpConditionMet(i.details.session.subtitle_stream.decision != "burn",
                                 i.details.session.subtitle_stream.decision),
        lambda i: dpAttributeIfExists(i.details.session.subtitle_stream, "location")
    ]


@registerAttributeType
class UserAttribute(SessionAttribute):
    name = "User"
    dataPoints = [
        lambda i: [u"%s @ %s" % (plexapp.ACCOUNT.title or plexapp.ACCOUNT.username or ' ', i.mediaItem.server.name)]
    ]


class SessionAttributes(OrderedDict):
    def __init__(self, ref, *args, **kwargs):
        self.ref = ref
        OrderedDict.__init__(self, *args, **kwargs)

        for name, cls in ATTRIBUTE_TYPES.iteritems():
            self[name] = instance = cls()
            instance.data = []
            if not instance.displayCondition or instance.displayCondition(self.ref):
                for dp in instance.dataPoints:
                    try:
                        result = dp(self.ref)
                        if result is not None:
                            instance.data += result
                    except:
                        pass


class VideoSessionInfo:
    def __init__(self, sessionMediaContainer, mediaContainer, incompleteSessionData=False):
        self.mediaItem = mediaContainer
        self.session = sessionMediaContainer

        if incompleteSessionData:
            #mediaContainerClone = buildItem(mediaContainer.server, mediaContainer._fulldata, initpath=mediaContainer.initpath, container=mediaContainer.container)#buildItem(mediaContainer._server, mediaContainer._data, mediaContainer._initPath)
            mediaContainerClone = listItems(mediaContainer.server, '/library/metadata/{0}'.format(mediaContainer.ratingKey))[0]
            self.session = mediaContainerClone

        self.details = MediaDetailsHolder(self.mediaItem, self.session, mediaContainer.mediaChoice)
        if incompleteSessionData:
            self.details.session.incompleteSessionDataToMedia(incompleteSessionData, self.session)

        self.attributes = SessionAttributes(self)

    def normRes(self, res):
        try:
            int(res)
        except:
            pass
        else:
            res += "p"
        return res
