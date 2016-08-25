from lib import player

import preplay
import subitems
import episodes
import photos
import posters
import playlist


def open(obj):
    if obj.TYPE in ('episode', 'movie'):
        return playableClicked(obj)
    elif obj.TYPE in ('show'):
        return showClicked(obj)
    elif obj.TYPE in ('artist'):
        return artistClicked(obj)
    elif obj.TYPE in ('season'):
        return seasonClicked(obj)
    elif obj.TYPE in ('album'):
        return albumClicked(obj)
    elif obj.TYPE in ('photo'):
        return photoClicked(obj)
    elif obj.TYPE in ('photodirectory'):
        return photoDirectoryClicked(obj)
    elif obj.TYPE in ('playlist'):
        return playlistClicked(obj)
    elif obj.TYPE in ('clip'):
        return player.PLAYER.playVideo(obj)


def handleOpen(winclass, **kwargs):
    try:
        w = winclass.open(**kwargs)
        return w.exitCommand
    except AttributeError:
        pass
    finally:
        del w

    return None


def playableClicked(playable):
    return handleOpen(preplay.PrePlayWindow, video=playable)


def showClicked(show):
    return handleOpen(subitems.ShowWindow, media_item=show)


def artistClicked(artist):
    return handleOpen(subitems.ArtistWindow, media_item=artist)


def seasonClicked(season):
    return handleOpen(episodes.EpisodesWindow, season=season)


def albumClicked(album):
    return handleOpen(episodes.AlbumWindow, season=album)


def photoClicked(photo):
    return handleOpen(photos.PhotoWindow, photo=photo)


def photoDirectoryClicked(photodirectory):
    return handleOpen(posters.SquaresWindow, section=photodirectory)


def playlistClicked(pl):
    return handleOpen(playlist.PlaylistWindow, playlist=pl)
