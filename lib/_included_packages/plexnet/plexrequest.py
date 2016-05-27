from xml.etree import ElementTree

import plexserver
import plexresult
import http


class PlexRequest(http.HttpRequest):
    def __init__(self, server, path, method=None):
        if not server:
            server = plexserver.dummyPlexServer()

        self.server = server
        self.path = path

        AddPlexHeaders(obj.request, server.GetToken())

    def onResponse(self, event, context):
        if context.get('completionCallback'):
            result = plexresult.PlexResult(self.server, self.path)
            result.SetResponse(event)
            context['completionCallback']([self, result, context])

    def doRequestWithTimeout(self, timeout=10, postBody=None):
        # non async request/response
        if postBody:
            xml.Parse(self.PostToStringWithTimeout(postBody, timeout))
        else:
            xml.Parse(m.GetToStringWithTimeout(timeout))

        response = plexresult.PlexResult(self.server, self.path)
        response.setResponse(self.event)
        response.parseFakeXMLResponse(xml)

        return response
