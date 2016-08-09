import xbmc
import xbmcplugin
import xbmcgui
import sys
import binascii
from lib import _included_packages
from plexnet import audio, plexplayer

HANDLE = int(sys.argv[1])


def main():
    if len(sys.argv) < 3:
        return

    data = sys.argv[2].split('?')[-1]

    from plexnet import plexobjects

    track = plexobjects.PlexObject.deSerialize(binascii.unhexlify(data))

    pobj = plexplayer.PlexAudioPlayer(track)
    url = pobj.build()['url']  # .streams[0]['url']
    xbmc.log('Playing URL: {0}'.format(url))
    url += '&X-Plex-Platform=Chrome'

    listitem = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem)

main()
