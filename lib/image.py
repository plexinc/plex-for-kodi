import os
import requests
import StringIO
from lib import util
try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


CACHE_PATH = os.path.join(util.PROFILE, 'avatars')

if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)


def getImage(url, ID):
    imagePath = os.path.join(CACHE_PATH, '{0}.png'.format(ID))
    backPath = os.path.join(CACHE_PATH, '{0}-blur.png'.format(ID))
    if os.path.exists(imagePath):
        if os.path.exists(backPath):
            return (imagePath, backPath)
        else:
            return (imagePath, '')

    if not HAS_PIL:
        return (url, '')

    img = Image.open(StringIO.StringIO(requests.get(url).content))
    img.save(imagePath)

    new = img.convert('RGB').filter(ImageFilter.GaussianBlur(radius=70))
    new.save(backPath)

    return (imagePath, backPath)
