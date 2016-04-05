import os
import requests
import StringIO
import xbmc
from lib import util
try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from PIL import ImageFont, ImageDraw
    HAS_FONT = True
except ImportError:
    HAS_FONT = False


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


def textToImage(text, size=200, w=800, h=200, color=(255, 255, 255)):
    if not HAS_FONT:
        return None

    fontPath = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8'), 'resources', 'font', 'DejaVuSans.ttf')
    outPath = os.path.join(util.PROFILE, 'text.png')

    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    usr_font = ImageFont.truetype(fontPath, size)
    d_usr = ImageDraw.Draw(image)
    d_usr.text((0, 0), text, color, font=usr_font)
    image.save(outPath)

    return outPath
