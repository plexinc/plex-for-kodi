import xbmc
import xbmcgui
from lib.util import T
import plexnet


def showAudioDialog(video):
    options = [s.getTitle() for s in video.audioStreams]
    idx = xbmcgui.Dialog().select('Select Audio Stream', options)
    if idx < 0:
        return

    video.selectStream(video.audioStreams[idx])


def showSubtitlesDialog(video):
    options = [(s, s.getTitle()) for s in video.subtitleStreams]
    options.insert(0, (plexnet.plexstream.NoneStream(), 'None'))
    idx = xbmcgui.Dialog().select('Select Subtitle Stream', [o[1] for o in options])
    if idx < 0:
        return

    video.selectStream(options[idx][0])


def showQualityDialog(video):
    options = [T(i) for i in (32001, 32002, 32003, 32004, 32005, 32006, 32007, 32008, 32009, 32010, 32011, 32012, 32013, 32014)]
    idx = xbmcgui.Dialog().select('Select Quality', options)
    if idx < 0:
        return

    idx = 13 - idx
    video.settings.setPrefOverride('local_quality', idx)
    video.settings.setPrefOverride('remote_quality', idx)
    video.settings.setPrefOverride('online_quality', idx)


def showDialog(video):
    while not xbmc.abortRequested:
        sas = video.selectedAudioStream()
        sss = video.selectedSubtitleStream()
        options = [
            ('audio', 'Audio: {0}'.format(sas and sas.getTitle() or 'None')),
            ('subs', 'Subtitles: {0}'.format(sss and sss.getTitle() or 'None')),
            ('quality', 'Quality: {0} {1} ({2})'.format(
                plexnet.util.bitrateToString(video.mediaChoice.media.bitrate.asInt() * 1000),
                video.mediaChoice.media.getVideoResolutionString(),
                video.mediaChoice.media.title
            ))
        ]

        idx = xbmcgui.Dialog().select('Select Quality', [o[1] for o in options])
        if idx < 0:
            return

        result = options[idx][0]

        if result == 'audio':
            showAudioDialog(video)
        elif result == 'subs':
            showSubtitlesDialog(video)
        elif result == 'quality':
            showQualityDialog(video)
