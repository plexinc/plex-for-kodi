import dropdown

from lib.util import T


def chooseVersion(video):
    if len(video.media) > 1:
        options = []
        for media in video.media:
            ind = ''
            if video.mediaChoice and media.id == video.mediaChoice.media.id:
                ind = 'script.plex/home/device/check.png'
            options.append({'key': media, 'display': media.versionString(), 'indicator': ind})
        choice = dropdown.showDropdown(options, header=T(32450, 'Choose Version'), with_indicator=True)
        if not choice:
            return False

        choice['key'].set('selected', 1)

    return True


def resetVersion(video):
    if len(video.media) < 2:
        return

    for media in video.media:
        media.set('selected', '')

    video.media[0].set('selected', 1)
