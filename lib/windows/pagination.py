# coding=utf-8
import kodigui


class MLCPaginator(object):
    """
    A paginator for ManagedListControl instances
    """
    control = None
    pageSize = 8
    orphans = pageSize / 2
    offset = 0
    leafCount = None
    parentWindow = None
    thumbFallback = None

    _direction = None
    _currentAmount = None
    _boundaryHit = False

    def __init__(self, control, parent_window, page_size=None, orphans=None, leaf_count=None):
        self.control = control
        self.pageSize = page_size if page_size is not None else self.pageSize
        self.orphans = orphans if orphans is not None else self.orphans
        self.leafCount = leaf_count
        self.parentWindow = parent_window

        self.reset()

    def reset(self):
        self._currentAmount = None
        self._boundaryHit = False
        self._direction = None

    def getData(self, offset, amount):
        raise NotImplementedError

    def createListItem(self, data):
        return self.parentWindow.createListItem(data)

    def prepareListItem(self, data, mli):
        pass

    def readyForPaging(self):
        return self.parentWindow.initialized

    @property
    def _readyForPaging(self):
        return self.readyForPaging()

    @property
    def boundaryHit(self):
        self._boundaryHit = False

        if not self._readyForPaging:
            return

        mli = self.control.getSelectedItem()
        if mli and mli.getProperty("is.boundary") and not mli.getProperty("is.updating"):
            direction = "left" if mli.getProperty("left.boundary") else "right"
            mli.setBoolProperty("is.updating", True)
            self.offset = int(mli.getProperty("orig.index"))
            self._direction = direction
            self._boundaryHit = True

        return self._boundaryHit

    @property
    def nextPage(self):
        leafCount = self.leafCount
        offset = self.offset
        amount = self.pageSize

        if self._direction == "left":
            # move the slice to the left by :amount: based on :offset:
            amount = min(offset, self.pageSize)
            offset -= amount

            # avoid short pages on the left end
            if 0 < offset < self.orphans:
                amount += offset
                offset = 0

        else:
            # move the slice to the right
            itemsLeft = leafCount - offset
            # avoid short pages on the right end
            if itemsLeft <= self.pageSize + self.orphans:
                amount = self.pageSize + self.orphans

        self.offset = offset
        data = self.getData(offset, amount)
        self._currentAmount = len(data)
        return data

    @property
    def initialPage(self):
        amount = self.pageSize
        if self.pageSize + self.orphans >= self.leafCount:
            amount = self.pageSize + self.orphans

        data = self.getData(self.offset, amount)
        self._currentAmount = len(data)
        return data

    def populate(self, items):
        idx = 0
        moreLeft = self.offset > 0
        moreRight = self.offset + self._currentAmount < self.leafCount

        thumbFallback = self.thumbFallback
        if callable(thumbFallback):
            mlis = [kodigui.ManagedListItem(properties={'thumb.fallback': thumbFallback(item)})
                    for item in items]
        else:
            mlis = [
                kodigui.ManagedListItem(properties={'thumb.fallback': thumbFallback} if thumbFallback else {})
                for x in range(len(items))]

        self.control.replaceItems(mlis)

        finalItems = []

        for item in items:
            mli = self.createListItem(item)

            if mli:
                mli.setProperty('index', str(idx))
                self.prepareListItem(item, mli)
                finalItems.append(mli)
                idx += 1

        if items:
            if moreRight:
                end = kodigui.ManagedListItem('')
                end.setBoolProperty('is.boundary', True)
                end.setBoolProperty('right.boundary', True)
                end.setProperty("orig.index", str(int(self.offset + self._currentAmount)))
                finalItems.append(end)

            if moreLeft:
                start = kodigui.ManagedListItem('')
                start.setBoolProperty('is.boundary', True)
                start.setBoolProperty('left.boundary', True)
                start.setProperty("orig.index", str(int(self.offset)))
                finalItems.insert(0, start)

        self.control.replaceItems(finalItems)
        self.selectItem(self._currentAmount, more_left=moreLeft, more_right=moreRight, items=items)

        return finalItems

    def selectItem(self, amount, more_left=False, more_right=False, items=None):
        if self._direction:
            if self._direction == "left":
                self.control.selectItem(amount - (1 if not more_left else 0))
                return True

            elif self._direction == "right":
                self.control.selectItem(1)
                return True

    def paginate(self):
        if self._boundaryHit:
            items = self.nextPage

        else:
            items = self.initialPage

        return self.populate(items)


class BaseRelatedPaginator(MLCPaginator):
    thumbFallback = lambda self, rel: 'script.plex/thumb_fallbacks/{0}.png'.format(
        rel.type in ('show', 'season', 'episode') and 'show' or 'movie')

    def createListItem(self, rel):
        return kodigui.ManagedListItem(
            rel.title or '',
            thumbnailImage=rel.defaultThumb.asTranscodedImageURL(*self.parentWindow.RELATED_DIM),
            data_source=rel
        )