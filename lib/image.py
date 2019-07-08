import os
from lib import util

CACHE_PATH = os.path.join(util.PROFILE, 'avatars')

if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)


def getImage(url, ID):
    return url, ''
