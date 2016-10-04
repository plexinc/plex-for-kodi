import kodigui

from lib import util


class SearchDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-search.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
    SECTION_BUTTONS = {
        901: 'all',
        902: 'movie',
        903: 'show',
        904: 'artist',
        905: 'photo'
    }

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.query = 'Not Implemented'

    def onFirstInit(self):
        self.setProperty('search.section', 'all')
        self.updateQuery()

    def onAction(self, action):
        try:
            pass
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if 1000 < controlID < 1037:
            self.letterClicked(controlID)
        elif controlID in self.SECTION_BUTTONS:
            self.sectionClicked(controlID)
        elif controlID == 951:
            self.deleteClicked()
        elif controlID == 952:
            self.letterClicked(1037)
        elif controlID == 953:
            self.clearClicked()

    def updateQuery(self):
        self.setProperty('search.query', self.query)

    def sectionClicked(self, controlID):
        section = self.SECTION_BUTTONS[controlID]
        self.setProperty('search.section', section)

    def letterClicked(self, controlID):
        letter = self.LETTERS[controlID - 1001]
        self.query += letter
        self.updateQuery()

    def deleteClicked(self):
        self.query = self.query[:-1]
        self.updateQuery()

    def clearClicked(self):
        self.query = ''
        self.updateQuery()


def dialog():
    w = SearchDialog.open()
    del w
