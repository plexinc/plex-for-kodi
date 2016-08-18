import xbmc
import xbmcplugin
import xbmcgui
import sys
import base64
from lib import _included_packages, plex, util
from plexnet import audio, plexplayer

HANDLE = int(sys.argv[1])


def LOG(msg):
    xbmc.log('script.plex (plugin): {0}'.format(msg))

util.LOG = LOG


def playTrack(track):
    apobj = plexplayer.PlexAudioPlayer(track)
    url = apobj.build()['url']
    LOG('Playing URL: {0}'.format(url))
    url += '&X-Plex-Platform=Chrome'

    return xbmcgui.ListItem(path=url)


def playVideo(video):
    return None


def play(data):
    try:
        from plexnet import plexobjects

        plexObject = plexobjects.PlexObject.deSerialize(base64.urlsafe_b64decode(data))

        if plexObject.type == 'track':
            listitem = playTrack(plexObject)
        elif plexObject.type in ('episode', 'movie', 'clip'):
            listitem = playVideo(plexObject)
    except:
        util.ERROR()
        xbmcplugin.setResolvedUrl(HANDLE, False, None)
        return

    xbmcplugin.setResolvedUrl(HANDLE, True, listitem)


def main():
    try:
        if len(sys.argv) < 3:
            return

        path = sys.argv[0].split('/', 3)[-1]
        data = sys.argv[2].lstrip('?')

        if path == 'play':
            play(data)
    except:
        util.ERROR()


main()
