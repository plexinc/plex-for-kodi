# coding=utf-8

from collections import OrderedDict

import util


class MediaDetails:
    details = None

    def __init__(self, mediaContainer, byRef=None):
        self.details = self.findMediaDetails(mediaContainer, byRef=byRef)

    def findMediaDetails(self, mediaList, byRef=None):
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

        for media in mediaList:
            for part in media.parts:
                if not byRef:
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
                    if part.id == byRef.part.id:
                        data["part"] = part
                        data["media"] = media

                        for stream in part.streams:
                            if stream.id == byRef.video_stream.id:
                                data["video_stream"] = stream

                            elif stream.id == byRef.audio_stream.id:
                                data["audio_stream"] = stream

                            elif stream.id == byRef.subtitle_stream.id:
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
        self.original = MediaDetails(originalMedia, byRef=self.session)


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
        lambda i: [u"%s @ %s" % (i.session.user.title, i.mediaItem.server.name)]
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
                        util.ERROR()


class VideoSessionInfo:
    def __init__(self, sessionMediaContainer, mediaContainer):
        self.mediaItem = mediaContainer
        self.session = sessionMediaContainer
        self.details = MediaDetailsHolder(self.mediaItem.media, self.session.media)
        self.attributes = SessionAttributes(self)

    def normRes(self, res):
        try:
            int(res)
        except:
            pass
        else:
            res += "p"
        return res
