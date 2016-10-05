
import busy

from plexnet import playqueue, plexapp
from lib import util


def open(obj):
    if isinstance(obj, playqueue.PlayQueue):
        util.DEBUG_LOG('waiting for playQueue to initialize')
        if busy.widthDialog(obj.waitForInitialization, None):
            util.DEBUG_LOG('playQueue initialized: {0}'.format(obj))
            if obj.type == 'audio':
                import musicplayer
                return handleOpen(musicplayer.MusicPlayerWindow, track=obj.current(), playlist=obj)
            elif obj.type == 'photo':
                import photos
                return handleOpen(photos.PhotoWindow, play_queue=obj)
            else:
                import videoplayer
                videoplayer.play(play_queue=obj)
                return ''
        else:
            util.DEBUG_LOG('playQueue timed out wating for initialization')
    elif isinstance(obj, basestring):
        key = obj
        if not obj.startswith('/'):
            key = '/library/metadata/{0}'.format(obj)
        return open(plexapp.SERVERMANAGER.selectedServer.getObject(key))
    elif obj.TYPE in ('episode', 'movie'):
        return playableClicked(obj)
    elif obj.TYPE in ('show'):
        return showClicked(obj)
    elif obj.TYPE in ('artist'):
        return artistClicked(obj)
    elif obj.TYPE in ('season'):
        return seasonClicked(obj)
    elif obj.TYPE in ('album'):
        return albumClicked(obj)
    elif obj.TYPE in ('photo',):
        return photoClicked(obj)
    elif obj.TYPE in ('photodirectory'):
        return photoDirectoryClicked(obj)
    elif obj.TYPE in ('playlist'):
        return playlistClicked(obj)
    elif obj.TYPE in ('clip'):
        import videoplayer
        videoplayer.play(video=obj)


def handleOpen(winclass, **kwargs):
    try:
        w = winclass.open(**kwargs)
        return w.exitCommand or ''
    except AttributeError:
        pass
    finally:
        del w

    return ''


def playableClicked(playable):
    import preplay
    return handleOpen(preplay.PrePlayWindow, video=playable)


def showClicked(show):
    import subitems
    return handleOpen(subitems.ShowWindow, media_item=show)


def artistClicked(artist):
    import subitems
    return handleOpen(subitems.ArtistWindow, media_item=artist)


def seasonClicked(season):
    import episodes
    return handleOpen(episodes.EpisodesWindow, season=season)


def albumClicked(album):
    import episodes
    return handleOpen(episodes.AlbumWindow, season=album)


def photoClicked(photo):
    import photos
    return handleOpen(photos.PhotoWindow, photo=photo)


def photoDirectoryClicked(photodirectory):
    import posters
    return handleOpen(posters.SquaresWindow, section=photodirectory)


def playlistClicked(pl):
    import playlist
    return handleOpen(playlist.PlaylistWindow, playlist=pl)
