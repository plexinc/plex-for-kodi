# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import time
import threading
import traceback


class BaseFunctions:
    xmlFile = ''
    path = ''
    theme = ''
    res = '720p'
    width = 1280
    height = 720

    usesGenerate = False

    def __init__(self):
        self.isOpen = True

    def onWindowFocus(self):
        # Not automatically called. Can be used by an external window manager
        pass

    def onClosed(self):
        pass

    @classmethod
    def open(cls, **kwargs):
        window = cls(cls.xmlFile, cls.path, cls.theme, cls.res, **kwargs)
        window.modal()
        return window

    @classmethod
    def create(cls, show=True, **kwargs):
        window = cls(cls.xmlFile, cls.path, cls.theme, cls.res, **kwargs)
        if show:
            window.show()
        window.isOpen = True
        return window

    def modal(self):
        self.isOpen = True
        self.doModal()
        self.onClosed()
        self.isOpen = False

    def activate(self):
        if not self._winID:
            self._winID = xbmcgui.getCurrentWindowId()
        xbmc.executebuiltin('ReplaceWindow({0})'.format(self._winID))

    def mouseXTrans(self, val):
        return int((val / self.getWidth()) * self.width)

    def mouseYTrans(self, val):
        return int((val / self.getHeight()) * self.height)

    def closing(self):
        return self._closing

    @classmethod
    def generate(self):
        return None

    def setProperties(self, prop_list, val_list_or_val):
        if isinstance(val_list_or_val, list) or isinstance(val_list_or_val, tuple):
            val_list = val_list_or_val
        else:
            val_list = [val_list_or_val] * len(prop_list)

        for prop, val in zip(prop_list, val_list):
            self.setProperty(prop, val)

    def propertyContext(self, prop, val='1'):
        return WindowProperty(self, prop, val)


class BaseWindow(xbmcgui.WindowXML, BaseFunctions):
    def __init__(self, *args, **kwargs):
        BaseFunctions.__init__(self)
        self._closing = False
        self._winID = None
        self.started = False
        self.finishedInit = False

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowId()
        if self.started:
            self.onReInit()
        else:
            self.started = True
            self.onFirstInit()
            self.finishedInit = True

    def onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def setProperty(self, key, value):
        if self._closing:
            return

        if not self._winID:
            self._winID = xbmcgui.getCurrentWindowId()

        try:
            xbmcgui.Window(self._winID).setProperty(key, value)
            xbmcgui.WindowXML.setProperty(self, key, value)
        except RuntimeError:
            traceback.print_exc()

    def doClose(self):
        if not self.isOpen:
            return
        self._closing = True
        self.isOpen = False
        self.close()

    def show(self):
        self._closing = False
        self.isOpen = True
        xbmcgui.WindowXML.show(self)

    def onClosed(self):
        pass


class BaseDialog(xbmcgui.WindowXMLDialog, BaseFunctions):
    def __init__(self, *args, **kwargs):
        BaseFunctions.__init__(self)
        self._closing = False
        self._winID = ''
        self.started = False

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowDialogId()
        if self.started:
            self.onReInit()

        else:
            self.started = True
            self.onFirstInit()

    def onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def setProperty(self, key, value):
        if self._closing:
            return

        if not self._winID:
            self._winID = xbmcgui.getCurrentWindowId()

        try:
            xbmcgui.Window(self._winID).setProperty(key, value)
            xbmcgui.WindowXMLDialog.setProperty(self, key, value)
        except RuntimeError:
            traceback.print_exc()

    def doClose(self):
        self._closing = True
        self.close()

    def show(self):
        self._closing = False
        xbmcgui.WindowXMLDialog.show(self)

    def onClosed(self):
        pass


class ManagedListItem(object):
    _properties = None

    def __init__(self, label='', label2='', iconImage='', thumbnailImage='', path='', data_source=None, properties=None):
        self._listItem = xbmcgui.ListItem(label, label2, iconImage, thumbnailImage, path)
        self.dataSource = data_source
        self.properties = {}
        self.label = label
        self.label2 = label2
        self.iconImage = iconImage
        self.thumbnailImage = thumbnailImage
        self.path = path
        self._ID = None
        self._manager = None
        self._valid = True
        if properties:
            for k, v in properties.items():
                self.setProperty(k, v)

    def __nonzero__(self):
        return self._valid

    @property
    def listItem(self):
        if not self._listItem:
            if not self._manager:
                return None
            self._listItem = self._manager.getListItemFromManagedItem(self)
        return self._listItem

    def _takeListItem(self, manager, lid):
        self._manager = manager
        self._ID = lid
        self._listItem.setProperty('__ID__', lid)
        li = self._listItem
        self._listItem = None
        self._manager._properties.update(self.properties)
        return li

    def _updateListItem(self):
        self.listItem.setProperty('__ID__', self._ID)
        self.listItem.setLabel(self.label)
        self.listItem.setLabel2(self.label2)
        self.listItem.setIconImage(self.iconImage)
        self.listItem.setThumbnailImage(self.thumbnailImage)
        self.listItem.setPath(self.path)
        for k in self._manager._properties.keys():
            self.listItem.setProperty(k, self.properties.get(k) or '')

    def pos(self):
        if not self._manager:
            return None
        return self._manager.getManagedItemPosition(self)

    def addContextMenuItems(self, items, replaceItems=False):
        self.listItem.addContextMenuItems(items, replaceItems)

    def addStreamInfo(self, stype, values):
        self.listItem.addStreamInfo(stype, values)

    def getLabel(self):
        return self.label

    def getLabel2(self):
        return self.label2

    def getProperty(self, key):
        return self.properties.get(key, '')

    def getdescription(self):
        return self.listItem.getdescription()

    def getduration(self):
        return self.listItem.getduration()

    def getfilename(self):
        return self.listItem.getfilename()

    def isSelected(self):
        return self.listItem.isSelected()

    def select(self, selected):
        return self.listItem.select(selected)

    def setArt(self, values):
        return self.listItem.setArt(values)

    def setIconImage(self, icon):
        self.iconImage = icon
        return self.listItem.setIconImage(icon)

    def setInfo(self, itype, infoLabels):
        return self.listItem.setInfo(itype, infoLabels)

    def setLabel(self, label):
        self.label = label
        return self.listItem.setLabel(label)

    def setLabel2(self, label):
        self.label2 = label
        return self.listItem.setLabel2(label)

    def setMimeType(self, mimetype):
        return self.listItem.setMimeType(mimetype)

    def setPath(self, path):
        self.path = path
        return self.listItem.setPath(path)

    def setProperty(self, key, value):
        if self._manager:
            self._manager._properties[key] = 1
        self.properties[key] = value
        return self.listItem.setProperty(key, value)

    def setSubtitles(self, subtitles):
        return self.listItem.setSubtitles(subtitles)  # List of strings - HELIX

    def setThumbnailImage(self, thumb):
        self.thumbnailImage = thumb
        return self.listItem.setThumbnailImage(thumb)


class ManagedControlList(object):
    def __init__(self, window, control_id, max_view_index):
        self.controlID = control_id
        self.window = window
        self.control = window.getControl(control_id)
        self.items = []
        self._sortKey = None
        self._idCounter = 0
        self._maxViewIndex = max_view_index
        self._properties = {}

    def __getattr__(self, name):
        return getattr(self.control, name)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self.items[idx]
        else:
            return self.getListItem(idx)

    def __iter__(self):
        for i in self.items:
            yield i

    def __len__(self):
        return self.size()

    def _updateItems(self, bottom=None, top=None):
        if bottom is None:
            bottom = 0
            top = self.size()

        for idx in range(bottom, top):
            li = self.control.getListItem(idx)
            mli = self.items[idx]
            mli._manager = self
            mli._listItem = li
            mli._updateListItem()

    def _nextID(self):
        self._idCounter += 1
        return str(self._idCounter)

    def reInit(self, window, control_id):
        self.controlID = control_id
        self.window = window
        self.control = window.getControl(control_id)
        self.control.addItems([i._takeListItem(self, self._nextID()) for i in self.items])

    def setSort(self, sort):
        self._sortKey = sort

    def addItem(self, managed_item):
        self.items.append(managed_item)
        self.control.addItem(managed_item._takeListItem(self, self._nextID()))

    def addItems(self, managed_items):
        self.items += managed_items
        self.control.addItems([i._takeListItem(self, self._nextID()) for i in managed_items])

    def replaceItems(self, managed_items):
        oldSize = self.size()

        for i in self.items:
            i._valid = False

        self.items = managed_items
        size = self.size()
        if size != oldSize:
            pos = self.getSelectedPosition()

            if size > oldSize:
                for i in range(0, size - oldSize):
                    self.control.addItem(xbmcgui.ListItem())
            elif size < oldSize:
                diff = oldSize - size
                idx = oldSize - 1
                while diff:
                    self.control.removeItem(idx)
                    idx -= 1
                    diff -= 1

            if self.positionIsValid(pos):
                self.selectItem(pos)
            elif pos >= size:
                self.selectItem(size - 1)

        self._updateItems(0, self.size())

    def getListItem(self, pos):
        li = self.control.getListItem(pos)
        mli = self.items[pos]
        mli._listItem = li
        return mli

    def getListItemByDataSource(self, data_source):
        for mli in self:
            if data_source == mli.dataSource:
                return mli
        return None

    def getSelectedItem(self):
        pos = self.control.getSelectedPosition()
        if not self.positionIsValid(pos):
            pos = self.size() - 1

        if pos < 0:
            return None
        return self.getListItem(pos)

    def removeItem(self, index):
        old = self.items.pop(index)
        old._valid = False

        self.control.removeItem(index)
        top = self.control.size() - 1
        if top < 0:
            return
        if top < index:
            index = top
        self.control.selectItem(index)

    def insertItem(self, index, managed_item):
        pos = self.getSelectedPosition() + 1

        if index >= self.size() or index < 0:
            self.addItem(managed_item)
        else:
            self.items.insert(index, managed_item)
            self.control.addItem(managed_item._takeListItem(self, self._nextID()))
            self._updateItems(index, self.size())

        if self.positionIsValid(pos):
            self.selectItem(pos)

    def moveItem(self, mli, dest_idx):
        source_idx = mli.pos()
        if source_idx < dest_idx:
            rstart = source_idx
            rend = dest_idx + 1
            # dest_idx-=1
        else:
            rstart = dest_idx
            rend = source_idx + 1
        mli = self.items.pop(source_idx)
        self.items.insert(dest_idx, mli)

        self._updateItems(rstart, rend)

    def swapItems(self, pos1, pos2):
        if not self.positionIsValid(pos1) or not self.positionIsValid(pos2):
            return False

        item1 = self.items[pos1]
        item2 = self.items[pos2]
        li1 = item1._listItem
        li2 = item2._listItem
        item1._listItem = li2
        item2._listItem = li1

        item1._updateListItem()
        item2._updateListItem()
        self.items[pos1] = item2
        self.items[pos2] = item1

        return True

    def shiftView(self, shift, hold_selected=False):
        if not self._maxViewIndex:
            return
        selected = self.getSelectedItem()
        selectedPos = selected.pos()
        viewPos = self.getViewPosition()

        if shift > 0:
            pushPos = selectedPos + (self._maxViewIndex - viewPos) + shift
            if pushPos >= self.size():
                pushPos = self.size() - 1
            self.selectItem(pushPos)
            newViewPos = self._maxViewIndex
        elif shift < 0:
            pushPos = (selectedPos - viewPos) + shift
            if pushPos < 0:
                pushPos = 0
            self.selectItem(pushPos)
            newViewPos = 0

        if hold_selected:
            self.selectItem(selected.pos())
        else:
            diff = newViewPos - viewPos
            fix = pushPos - diff
            # print '{0} {1} {2}'.format(newViewPos, viewPos, fix)
            if self.positionIsValid(fix):
                self.selectItem(fix)

    def reset(self):
        for i in self.items:
            i._valid = False
        self.items = []
        self.control.reset()

    def size(self):
        return len(self.items)

    def getViewPosition(self):
        try:
            return int(xbmc.getInfoLabel('Container({0}).Position'.format(self.controlID)))
        except:
            return 0

    def getViewRange(self):
        viewPosition = self.getViewPosition()
        selected = self.getSelectedPosition()
        return range(max(selected - viewPosition, 0), min(selected + (self._maxViewIndex - viewPosition) + 1, self.size() - 1))

    def positionIsValid(self, pos):
        return 0 <= pos < self.size()

    def sort(self, sort=None, reverse=False):
        sort = sort or self._sortKey

        self.items.sort(key=sort, reverse=reverse)

        self._updateItems(0, self.size())

    def reverse(self):
        self.items.reverse()
        self._updateItems(0, self.size())

    def getManagedItemPosition(self, mli):
        return self.items.index(mli)

    def getListItemFromManagedItem(self, mli):
        pos = self.items.index(mli)
        return self.control.getListItem(pos)

    def topHasFocus(self):
        return self.getSelectedPosition() == 0

    def bottomHasFocus(self):
        return self.getSelectedPosition() == self.size() - 1

    def newControl(self, window=None, control_id=None):
        self.controlID = control_id or self.controlID
        self.window = window or self.window
        self.control = self.window.getControl(self.controlID)
        self.control.addItems([xbmcgui.ListItem() for i in range(self.size())])
        self._updateItems()


class _MWBackground(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        self._multiWindow = kwargs.get('multi_window')
        self.started = False
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        if self.started:
            return
        self.started = True
        self._multiWindow._open()
        self.close()


class MultiWindow(object):
    def __init__(self, windows=None, default_window=None, **kwargs):
        self._windows = windows
        self._next = default_window or self._windows[0]
        self._properties = {}
        self._current = None
        self._currentOnInit = None
        self._allClosed = False
        self.exitCommand = None

    def __getattr__(self, name):
        return getattr(self._current, name)

    def nextWindow(self, window=None):
        if not window:
            idx = self._windows.index(self._current.__class__)
            idx += 1
            if idx >= len(self._windows):
                idx = 0
            window = self._windows[idx]

        self._next = window
        self._current.doClose()
        return self._next

    def _setupCurrent(self, cls):
        self._current = cls(cls.xmlFile, cls.path, cls.theme, cls.res)
        self._current.onFirstInit = self._onFirstInit
        self._current.onReInit = self.onReInit
        self._current.onClick = self.onClick
        self._current.onFocus = self.onFocus

        self._currentOnAction = self._current.onAction
        self._current.onAction = self.onAction

    @classmethod
    def open(cls, **kwargs):
        mw = cls(**kwargs)
        b = _MWBackground(mw.bgXML, mw.path, mw.theme, mw.res, multi_window=mw)
        b.doModal()
        return mw

    def _open(self):
        while not xbmc.abortRequested and not self._allClosed:
            self._setupCurrent(self._next)
            self._current.doModal()

        self._current.doClose()

    def setProperty(self, key, value):
        self._properties[key] = value
        self._current.setProperty(key, value)

    def _onFirstInit(self):
        for k, v in self._properties.items():
            self._current.setProperty(k, v)
        self.onFirstInit()

    def doClose(self):
        self._allClosed = True
        self._current.doClose()

    def onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def onAction(self, action):
        if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
            self.doClose()
        self._currentOnAction(action)

    def onClick(self, controlID):
        pass

    def onFocus(self, controlID):
        pass


class SafeControlEdit(object):
    CHARS_LOWER = 'abcdefghijklmnopqrstuvwxyz'
    CHARS_UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    CHARS_NUMBERS = '0123456789'
    CURSOR = '[COLOR FFCC7B19]|[/COLOR]'

    def __init__(self, control_id, label_id, window, key_callback=None, grab_focus=False):
        self.controlID = control_id
        self.labelID = label_id
        self._win = window
        self._keyCallback = key_callback
        self.grabFocus = grab_focus
        self._text = ''
        self.setup()

    def setup(self):
        self._labelControl = self._win.getControl(self.labelID)
        self._winOnAction = self._win.onAction
        self._win.onAction = self.onAction
        self.updateLabel()

    def onAction(self, action):
        try:
            controlID = self._win.getFocusId()
            if controlID == self.controlID:
                if self.processAction(action.getId()):
                    return
            elif self.grabFocus:
                if self.processOffControlAction(action.getButtonCode()):
                    self._win.setFocusId(self.controlID)
                    return
        except:
            traceback.print_exc()

        self._winOnAction(action)

    def processAction(self, action_id):
        if 61793 <= action_id <= 61818:  # Lowercase
            self.processChar(self.CHARS_LOWER[action_id - 61793])
        elif 61761 <= action_id <= 61786:  # Uppercase
            self.processChar(self.CHARS_UPPER[action_id - 61761])
        elif 61744 <= action_id <= 61753:
            self.processChar(self.CHARS_NUMBERS[action_id - 61744])
        elif action_id == 61728:  # Space
            self.processChar(' ')
        elif action_id == 61448:
            self.delete()
        else:
            return False

        if self._keyCallback:
            self._keyCallback()

        return True

    def processOffControlAction(self, action_id):
        if 61505 <= action_id <= 61530:  # Lowercase
            self.processChar(self.CHARS_LOWER[action_id - 61505])
        elif 192577 <= action_id <= 192602:  # Uppercase
            self.processChar(self.CHARS_UPPER[action_id - 192577])
        elif 61488 <= action_id <= 61497:
            self.processChar(self.CHARS_NUMBERS[action_id - 61488])
        elif 61552 <= action_id <= 61561:
            self.processChar(self.CHARS_NUMBERS[action_id - 61552])
        elif action_id == 61472:  # Space
            self.processChar(' ')
        # elif action_id == 61448:
        #     self.delete()
        else:
            return False

        if self._keyCallback:
            self._keyCallback()

        return True

    def updateLabel(self):
        self._labelControl.setLabel(self._text + self.CURSOR)

    def processChar(self, char):
        self._text += char
        self.updateLabel()

    def setText(self, text):
        self._text = text
        self.updateLabel()

    def getText(self):
        return self._text

    def append(self, text):
        self._text += text
        self.updateLabel()

    def delete(self):
        self._text = self._text[:-1]
        self.updateLabel()


class MultiSelectDialog(BaseDialog):
    xmlFile = ''
    path = ''
    theme = ''
    res = '720p'

    OPTIONS_LIST_ID = 0
    OK_BUTTON_ID = 0
    CANCEL_BUTTON_ID = 0
    USE_DEFAULT_BUTTON_ID = 0

    HELP_TEXTBOX_ID = 0

    TOGGLE_MOVE_DIVIDER_X = 0

    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args, **kwargs)
        self.options = kwargs.get('options', [])
        self.default = kwargs.get('default', False)
        self.moving = None
        self.right = True
        self.lastFocus = self.OPTIONS_LIST_ID
        self.helpTextBox = None
        self.result = []

    def onFirstInit(self):
        self.getControl(self.USE_DEFAULT_BUTTON_ID).setVisible(not self.default)
        self.optionsList = ManagedControlList(self, self.OPTIONS_LIST_ID, 8)
        self.helpTextBox = self.getControl(self.HELP_TEXTBOX_ID)
        self.setProperty('right', '1')
        self.fillOptionsList()

    def fillOptionsList(self):
        items = []
        for k, d, s in self.options:
            item = ManagedListItem(d, data_source=k)
            item.setProperty('selected', s and '1' or '')
            if s:
                self.result.append(k)
            items.append(item)

        self.optionsList.addItems(items)
        xbmc.sleep(200)
        self.setFocusId(self.OPTIONS_LIST_ID)

    def onClick(self, controlID):
        if controlID == self.OPTIONS_LIST_ID:
            if self.right:
                self.moveItem()
            else:
                self.optionClicked()
            return
        elif controlID == self.OK_BUTTON_ID:
            self.finish()
            self.doClose()
            return
        elif controlID == self.CANCEL_BUTTON_ID:
            self.result = False
            self.doClose()
            return
        elif controlID == self.USE_DEFAULT_BUTTON_ID:
            self.result = None
            self.doClose()
            return

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_MOUSE_MOVE and not self.moving:
                if self.getFocusId() == self.OPTIONS_LIST_ID:
                    if self.mouseXTrans(action.getAmount1()) < self.TOGGLE_MOVE_DIVIDER_X:
                        self.setRight(False)
                    else:
                        self.setRight()

            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                self.result = False
                self.doClose()
                return
            elif action in (
                xbmcgui.ACTION_MOVE_UP,
                xbmcgui.ACTION_MOVE_DOWN,
                xbmcgui.ACTION_MOUSE_MOVE,
                xbmcgui.ACTION_MOUSE_WHEEL_UP,
                xbmcgui.ACTION_MOUSE_WHEEL_DOWN
            ):
                if self.getFocusId() == self.OPTIONS_LIST_ID:
                    self.moveItem(True)

                self.lastFocus = self.getFocusId()
                return
            elif action == xbmcgui.ACTION_MOVE_LEFT:
                if self.lastFocus == self.OPTIONS_LIST_ID:
                    if self.right and not self.moving:
                        self.setRight(False)
                        self.lastFocus = self.getFocusId()
                        return
            elif action == xbmcgui.ACTION_MOVE_RIGHT:
                if self.lastFocus == self.OPTIONS_LIST_ID:
                    if not self.right:
                        self.setRight()
                        self.setFocusId(self.OPTIONS_LIST_ID)
                        self.lastFocus = self.OPTIONS_LIST_ID
                        return

        except:
            BaseDialog.onAction(self, action)
            import traceback
            traceback.print_exc()
            self.lastFocus = self.getFocusId()
            return

        self.lastFocus = self.getFocusId()
        BaseDialog.onAction(self, action)

    def onFocus(self, controlID):
        if self.moving:
            self.setHelp('Click again to finish the move')
            return

        if controlID == 201:
            self.setHelp('Click to save this setting')
        elif controlID == 202:
            self.setHelp('Click to discard changes')
        elif controlID == 203:
            self.setHelp('Click to ignore this setting and use the default')
        elif controlID == 300:
            if self.right:
                self.setHelp('Click to start moving the selected item')
            else:
                self.setHelp('Click to toggle the selected item')

    def setRight(self, right=True):
        self.right = right
        self.setProperty('right', right and '1' or '')
        if self.right:
            self.setHelp('Click to start moving the selected item')
        else:
            self.setHelp('Click to toggle the selected item')

    def setHelp(self, text):
        if not self.helpTextBox:
            return
        self.helpTextBox.setText(text)

    def optionClicked(self):
        item = self.optionsList.getSelectedItem()
        item.setProperty('selected', not item.getProperty('selected') and '1' or '')

    def moveItem(self, move=False):
        if move:
            if self.moving:
                pos = self.optionsList.getSelectedPosition()
                self.optionsList.moveItem(self.moving, pos)
        else:
            if self.moving:
                self.moving.setProperty('moving', '')
                self.moving = None
                self.onFocus(self.OPTIONS_LIST_ID)
            else:
                item = self.optionsList.getSelectedItem()
                self.moving = item
                item.setProperty('moving', '1')
                self.onFocus(self.OPTIONS_LIST_ID)

    def finish(self):
        self.result = []
        for o in self.optionsList:
            if o.getProperty('selected'):
                self.result.append(o.dataSource)


class PropertyTimer():
    def __init__(self, window_id, timeout, property_, value, addon_id=None, callback=None):
        self._winID = window_id
        self._timeout = timeout
        self._property = property_
        self._value = value
        self._endTime = 0
        self._thread = None
        self._addonID = addon_id
        self._closeWin = None
        self._closed = False
        self._callback = callback

    def _onTimeout(self):
        self._endTime = 0
        xbmcgui.Window(self._winID).setProperty(self._property, self._value)
        if self._addonID:
            xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self._property), self._value)
        if self._closeWin:
            self._closeWin.doClose()
        if self._callback:
            self._callback()

    def _wait(self):
        while not xbmc.abortRequested and time.time() < self._endTime:
            xbmc.sleep(100)
        if xbmc.abortRequested:
            return
        if self._endTime == 0:
            return
        self._onTimeout()

    def _stopped(self):
        return not self._thread or not self._thread.isAlive()

    def _reset(self):
        self._endTime = time.time() + self._timeout

    def _start(self):
        self._thread = threading.Thread(target=self._wait)
        self._thread.start()

    def stop(self, trigger=False):
        self._endTime = trigger and 1 or 0
        if not self._stopped():
            self._thread.join()

    def close(self):
        self._closed = True
        self.stop()

    def init(self, val):
        xbmcgui.Window(self._winID).setProperty(self._property, val)
        if self._addonID:
            xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self._property), val)

    def reset(self, close_win=None, init=None):
        if init:
            self.init(init)

        if self._closed:

            return
        if not self._timeout:
            return

        self._closeWin = close_win
        self._reset()

        if self._stopped:
            self._start()


class WindowProperty():
    def __init__(self, win, prop, val='1'):
        self.win = win
        self.prop = prop
        self.val = val

    def __enter__(self):
        self.win.setProperty(self.prop, self.val)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.win.setProperty(self.prop, '')


class GlobalProperty():
    def __init__(self, prop, val='1'):
        import xbmcaddon
        self.addonID = xbmcaddon.Addon().getInfo('id')
        self.prop = prop
        self.val = val

    def __enter__(self):
        xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self.prop), self.val)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self.prop), '')
