import http
import plexresource


class PlexResult(http.HttpResponse):
    def __init__(self, server, address):
        self.server = server
        self.address = address
        self.container = None
        self.parsed = None

    def setResponse(self, event):
        self.event = event

    def parseResponse(self):
        if self.parsed:
            return self.parsed

        self.parsed = False

        if self.isSuccess():
            data = self.getBodyXml()
            if data is not None:
                self.container = plexresource.PlexContainer(data, initpath=self.address, server=self.server)
                self.parsed = True

        return self.parsed

    def parseFakeXMLResponse(self, data):
        if self.parsed:
            return self.parsed

        self.parsed = False

        if data is not None:
            self.container = plexresource.PlexContainer(data, initpath=self.address, server=self.server)
            self.parsed = True

        return self.parsed
