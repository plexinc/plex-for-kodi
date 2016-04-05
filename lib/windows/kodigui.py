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

    @classmethod
    def open(cls, **kwargs):
        window = cls(cls.xmlFile, cls.path, cls.theme, cls.res, **kwargs)
        window.modal()
        return window

    @classmethod
    def create(cls, **kwargs):
        window = cls(cls.xmlFile, cls.path, cls.theme, cls.res, **kwargs)
        window.show()
        window.isOpen = True
        return window

    def modal(self):
        self.isOpen = True
        self.doModal()
        self.isOpen = False

    def mouseXTrans(self, val):
        return int((val / self.getWidth()) * self.width)

    def mouseYTrans(self, val):
        return int((val / self.getHeight()) * self.height)

    def closing(self):
        return self._closing

    @classmethod
    def generate(self):
        return None


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

    def onFirstInit(self): pass

    def onReInit(self): pass

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
        xbmcgui.WindowXML.show(self)

    def onClosed(self): pass


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

    def onFirstInit(self): pass

    def onReInit(self): pass

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

    def onClosed(self): pass


class ManagedListItem(object):
    _properties = None

    def __init__(self, label='', label2='', iconImage='', thumbnailImage='', path='', data_source=None):
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

    @classmethod
    def _addProperty(cls, prop):
        if not cls._properties:
            cls._properties = {}
        cls._properties[prop] = 1

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
        return li

    def _updateListItem(self):
        self.listItem.setProperty('__ID__', self._ID)
        self.listItem.setLabel(self.label)
        self.listItem.setLabel2(self.label2)
        self.listItem.setIconImage(self.iconImage)
        self.listItem.setThumbnailImage(self.thumbnailImage)
        self.listItem.setPath(self.path)
        for k in self.__class__._properties.keys():
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
        self.__class__._addProperty(key)
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
        self.sort = None
        self._idCounter = 0
        self._maxViewIndex = max_view_index

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

    def _updateItems(self, bottom, top):
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
                pos = self.getSelectedPosition()
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
            rend = dest_idx+1
            # dest_idx-=1
        else:
            rstart = dest_idx
            rend = source_idx+1
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

    def sort(self, sort=None):
        sort = sort or self._sortKey

        self.items.sort(key=self._sortKey)

        self._updateItems(0, self.size)

    def getManagedItemPosition(self, mli):
        return self.items.index(mli)

    def getListItemFromManagedItem(self, mli):
        pos = self.items.index(mli)
        return self.control.getListItem(pos)

    def topHasFocus(self):
        return self.getSelectedPosition() == 0

    def bottomHasFocus(self):
        return self.getSelectedPosition() == self.size() - 1


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
    def __init__(self, window_id, timeout, property_, value, addon_id=None):
        self._winID = window_id
        self._timeout = timeout
        self._property = property_
        self._value = value
        self._endTime = 0
        self._thread = None
        self._addonID = addon_id
        self._closeWin = None
        self._closed = False

    def _onTimeout(self):
        self._endTime = 0
        xbmcgui.Window(self._winID).setProperty(self._property, self._value)
        if self._addonID:
            xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self._property), self._value)
        if self._closeWin:
            self._closeWin.doClose()

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

    def stop(self):
        self._endTime = 0
        if not self._stopped():
            self._thread.join()

    def close(self):
        self._closed = True
        self.stop()

    def reset(self, close_win=None):
        if self._closed:
            return
        if not self._timeout:
            return
        self._closeWin = close_win
        self._reset()
        if self._stopped:
            self._start()
