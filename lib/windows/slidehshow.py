import time
import random

import kodigui

from lib import util
from plexnet import plexapp

class Slideshow(kodigui.BaseWindow, util.CronReceiver):
    xmlFile = 'script-plex-slideshow.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    TIME_BETWEEN_IMAGES = 15
    TIME_HIDE_TITLE_IN_QUIZ = 5
    TIME_DISPLAY_MOVE = 60
    
    CONTROL_INFO_GROUP = 100
    
    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.timeBetweenImages = self.TIME_BETWEEN_IMAGES
        self.timeBetweenDisplayMove = self.TIME_DISPLAY_MOVE
        self.timeTitleIsHidden = self.TIME_HIDE_TITLE_IN_QUIZ
        self.quizMode = util.advancedSettings.screensaverQuiz
        self.initialized = False

    def onFirstInit(self):
        self.setProperty('clock', '')
        self.setProperty('title', '')
        self.setProperty('thumb', '')
        self.setProperty('align', '0')
        
        self.infoGroupControl = self.getControl(self.CONTROL_INFO_GROUP)
        
        util.CRON.registerReceiver(self)
        self.timeFormat = util.timeFormat.replace(":%S", "")
        self.lastTime = ''
        self.displayPosition = 0
        self.changeTime = time.time() - 1
        self.displayMoveTime = time.time() + self.timeBetweenDisplayMove
        self.revealTitleTime = None
        
        self.selectedServer = plexapp.SERVERMANAGER.selectedServer
        self.index = -1
        self.images = []
        
        self.initialized = True
    
    def tick(self):
        if not self.initialized:
            return

        currentTime = time.time()
        timestr = time.strftime(self.timeFormat, time.localtime(currentTime))
        if not util.padHour and timestr[0] == "0" and timestr[1] != ":":
            timestr = timestr[1:]

        if currentTime > self.changeTime:
            nextIndex = self.index + 1
            
            if nextIndex >= len(self.images):
                if self.selectedServer != None:
                    self.images = self.selectedServer.library.randomArts();
                    util.DEBUG_LOG('[SS] Fetched {0} items'.format(len(self.images)))
                    nextIndex = 0

            if len(self.images) == 0:
                title = 'No Images'
                url = ''
            else:
                image = self.images[nextIndex]
                title = image.get('title')
                key = image.get('key')
                url = self.selectedServer.getImageTranscodeURL(key, self.width, self.height)
            if not self.quizMode:
                self.setProperty('title', title)
            else:
                self.setProperty('title', '')
                self.quizTitle = title
                self.revealTitleTime = currentTime + self.timeTitleIsHidden
            self.setProperty('thumb', url)

            self.index = nextIndex
            self.changeTime = time.time() + self.timeBetweenImages
        
        if self.revealTitleTime != None and currentTime > self.revealTitleTime:
            self.setProperty('title', self.quizTitle)
            self.revealTitleTime = None

        if currentTime > self.displayMoveTime:
            oldDisplayPosition = self.displayPosition
            self.displayPosition = (oldDisplayPosition + random.randint(1, 3)) % 4
            
            if (oldDisplayPosition&2) != (self.displayPosition&2):
                self.setProperty('align', str((self.displayPosition&2)>>1))

            if (oldDisplayPosition&1) != (self.displayPosition&1):
                newY = self.height - self.infoGroupControl.getY() - self.infoGroupControl.getHeight()
                self.infoGroupControl.setPosition(self.infoGroupControl.getX(), newY)
            
            self.displayMoveTime = currentTime + self.timeBetweenDisplayMove
        
        if timestr != self.lastTime:
            self.setProperty('clock', timestr)