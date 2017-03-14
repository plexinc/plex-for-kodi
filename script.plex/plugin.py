import xbmc
import xbmcplugin
import xbmcgui
import sys
import base64
from lib import _included_packages, plex, util
from plexnet import audio, plexplayer, plexapp

HANDLE = int(sys.argv[1])


def LOG(msg):
    xbmc.log('script.plex (plugin): {0}'.format(msg))


util.LOG = LOG


def playTrack(track):
    track.reload()
    apobj = plexplayer.PlexAudioPlayer(track)
    url = apobj.build()['url']
    url = util.addURLParams(url, {
        'X-Plex-Platform': 'Chrome',
        'X-Plex-Client-Identifier': plexapp.INTERFACE.getGlobal('clientIdentifier')
    })
    LOG('Playing URL: {0}'.format(url))

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
        else:  # This is a hack since it's both a plugin and a script. My Addons and Shortcuts otherwise can't launch the add-on
            xbmc.executebuiltin('Action(back)')  # This sometimes works to back out of the plugin directory display
            xbmc.executebuiltin('RunScript(script.plex)')
    except:
        util.ERROR()


main()
