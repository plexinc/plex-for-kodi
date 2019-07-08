import busy

from plexnet import playqueue, plexapp, plexlibrary
from lib import util


def open(obj, auto_play=False):
    if isinstance(obj, playqueue.PlayQueue):
        if busy.widthDialog(obj.waitForInitialization, None):
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
    elif isinstance(obj, basestring):
        key = obj
        if not obj.startswith('/'):
            key = '/library/metadata/{0}'.format(obj)
        return open(plexapp.SERVERMANAGER.selectedServer.getObject(key))
    elif obj.TYPE == 'episode':
        if not auto_play:
            return episodeClicked(obj)
        return playableClicked(obj, auto_play=auto_play)
    elif obj.TYPE == 'movie':
        return playableClicked(obj, auto_play=auto_play)
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
    elif obj.TYPE in ('track'):
        return trackClicked(obj)
    elif obj.TYPE in ('playlist'):
        return playlistClicked(obj)
    elif obj.TYPE in ('clip'):
        import videoplayer
        return videoplayer.play(video=obj)
    elif obj.TYPE in ('Genre'):
        return genreClicked(obj)
    elif obj.TYPE in ('Director'):
        return directorClicked(obj)
    elif obj.TYPE in ('Role'):
        return actorClicked(obj)


def handleOpen(winclass, **kwargs):
    w = None
    try:
        w = winclass.open(**kwargs)
        return w.exitCommand or ''
    except AttributeError:
        pass
    finally:
        del w
        util.garbageCollect()

    return ''


def playableClicked(playable, auto_play=False):
    import preplay
    return handleOpen(preplay.PrePlayWindow, video=playable, auto_play=auto_play)


def episodeClicked(episode):
    import episodes
    return handleOpen(episodes.EpisodesWindow, episode=episode)


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
    import tracks
    return handleOpen(tracks.AlbumWindow, album=album)


def photoClicked(photo):
    import photos
    return handleOpen(photos.PhotoWindow, photo=photo)


def trackClicked(track):
    import musicplayer
    return handleOpen(musicplayer.MusicPlayerWindow, track=track)


def photoDirectoryClicked(photodirectory):
    return sectionClicked(photodirectory)


def playlistClicked(pl):
    import playlist
    return handleOpen(playlist.PlaylistWindow, playlist=pl)


def sectionClicked(section, filter_=None):
    import library
    library.ITEM_TYPE = section.TYPE
    key = section.key
    if not key.isdigit():
        key = section.getLibrarySectionId()
    viewtype = util.getSetting('viewtype.{0}.{1}'.format(section.server.uuid, key))
    if section.TYPE in ('artist', 'photo', 'photodirectory'):
        default = library.VIEWS_SQUARE.get(viewtype)
        return handleOpen(
            library.LibraryWindow, windows=library.VIEWS_SQUARE.get('all'), default_window=default, section=section, filter_=filter_
        )
    else:
        default = library.VIEWS_POSTER.get(viewtype)
        return handleOpen(
            library.LibraryWindow, windows=library.VIEWS_POSTER.get('all'), default_window=default, section=section, filter_=filter_
        )


def genreClicked(genre):
    section = plexlibrary.LibrarySection.fromFilter(genre)
    filter_ = {'type': genre.FILTER, 'display': 'Genre', 'sub': {'val': genre.id, 'display': genre.tag}}
    return sectionClicked(section, filter_)


def directorClicked(director):
    section = plexlibrary.LibrarySection.fromFilter(director)
    filter_ = {'type': director.FILTER, 'display': 'Director', 'sub': {'val': director.id, 'display': director.tag}}
    return sectionClicked(section, filter_)


def actorClicked(actor):
    section = plexlibrary.LibrarySection.fromFilter(actor)
    filter_ = {'type': actor.FILTER, 'display': 'Actor', 'sub': {'val': actor.id, 'display': actor.tag}}
    return sectionClicked(section, filter_)
