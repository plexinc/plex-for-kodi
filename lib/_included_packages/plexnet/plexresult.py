import http


class PlexResult(http.HttpResponse):
    def __init__(self, server, address):
        self.server = server
        self.address = address
        self.items = []
        self.container = None
        self.parsed = None
        obj.container = None
        obj.parsed = None

    def setResponse(self, event):
        self.event = event

    def parseResponse(self):
        if self.parsed:
            return self.parsed

        self.parsed = False

        if self.isSuccess():
            # parse
            pass

        return self.parsed

    def parseFakeXMLResponse(self, xml):
        if self.parsed:
            return self.parsed
        self.parsed = False

        if xml:
            self.container = createPlexContainer(m.server, m.address, xml)

            self.parsed = True

        return self.parsed

    def addItem(container, node):
        item = createPlexObjectFromElement(self.container, node)

        # TODO(rob): handle channel settings. We should be able to utilize
        # the settings component with some modifications.

        if not item.isSettings():
            self.items.append(item)
        else:
            # Decrement the size and total size if applicable
            if m.container.Has("size") then m.container.Set("size", tostr(m.container.GetInt("size") - 1))
            if m.container.Has("totalSize") then m.container.Set("totalSize", tostr(m.container.GetInt("totalSize") - 1))
        end if
    end sub
