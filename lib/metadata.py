from plexnet import media
from util import T


EXTRA_MAP = {
    media.METADATA_RELATED_TRAILER: T(32201, 'Trailer'),
    media.METADATA_RELATED_DELETED_SCENE: T(32202, 'Deleted Scene'),
    media.METADATA_RELATED_INTERVIEW: T(32203, 'Interview'),
    media.METADATA_RELATED_MUSIC_VIDEO: T(32204, 'Music Video'),
    media.METADATA_RELATED_BEHIND_THE_SCENES: T(32205, 'Behind the Scenes'),
    media.METADATA_RELATED_SCENE_OR_SAMPLE: T(32206, 'Scene/Sample'),
    media.METADATA_RELATED_LIVE_MUSIC_VIDEO: T(32207, 'Live Music Video'),
    media.METADATA_RELATED_LYRIC_MUSIC_VIDEO: T(32208, 'Lyric Music Video'),
    media.METADATA_RELATED_CONCERT: T(32209, 'Concert'),
    media.METADATA_RELATED_FEATURETTE: T(32210, 'Featurette'),
    media.METADATA_RELATED_SHORT: T(32211, 'Short'),
    media.METADATA_RELATED_OTHER: T(32212, 'Other')
}


API_TRANSLATION_MAP = {
    'Unknown': T(32441),
    'Embedded': T(32442),
    'Forced': T(32443),
    'Lyrics': T(32444),
    'Mono': T(32445),
    'Stereo': T(32446),
    'None': T(32447)
}


def apiTranslate(string):
    return API_TRANSLATION_MAP.get(string) or string
