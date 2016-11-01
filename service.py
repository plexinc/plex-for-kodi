# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon


def main():
    if xbmcaddon.Addon().getSetting('kiosk.mode') == 'true':
        xbmc.log('script.plex: Starting from service (Kiosk Mode)', xbmc.LOGNOTICE)
        xbmc.executebuiltin('RunScript(script.plex)')


if __name__ == '__main__':
    main()
