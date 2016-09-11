import kodigui

from lib import util


class DropdownDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-dropdown.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    GROUP_ID = 100
    OPTIONS_LIST_ID = 250

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.options = kwargs.get('options')
        self.pos = kwargs.get('pos')
        self.posIsBottom = kwargs.get('pos_is_bottom')
        self.closeDirection = kwargs.get('close_direction')
        self.choice = None

    def onFirstInit(self):
        self.optionsList = kodigui.ManagedControlList(self, self.OPTIONS_LIST_ID, 8)
        self.showOptions()
        height = (len(self.options) * 66) + 80
        y = self.pos[1]
        if self.posIsBottom:
            y -= height
        self.getControl(100).setPosition(self.pos[0], y)
        self.getControl(110).setHeight(height)
        self.setProperty('show', '1')
        self.setProperty('close.direction', self.closeDirection)

    def onAction(self, action):
        try:
            pass
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.OPTIONS_LIST_ID:
            self.setChoice()

    def setChoice(self):
        mli = self.optionsList.getSelectedItem()
        if not mli:
            return

        self.choice = self.options[self.optionsList.getSelectedPosition()][0]
        self.doClose()

    def showOptions(self):
        items = []
        for o in self.options:
            item = kodigui.ManagedListItem(o[1], data_source=o[0])
            items.append(item)

        if len(items) > 1:
            items[0].setProperty('first', '1')
            items[-1].setProperty('last', '1')
        elif items:
            items[0].setProperty('only', '1')

        self.optionsList.reset()
        self.optionsList.addItems(items)

        self.setFocusId(self.OPTIONS_LIST_ID)


def showDropdown(options, pos=(0, 0), pos_is_bottom=False, close_direction='top'):
    w = DropdownDialog.open(options=options, pos=pos, pos_is_bottom=pos_is_bottom, close_direction=close_direction)
    choice = w.choice
    del w
    return choice
