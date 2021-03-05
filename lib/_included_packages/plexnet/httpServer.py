from __future__ import print_function

import threading
import time
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from lxml import etree as ET
from urlparse import urlparse, parse_qs

from lib import util
from gdmClient import GDMClientDiscovery


class Subscription:
    def __init__(self, client_id, command_id=0):
        self.id = client_id  # id of the subscribed controller
        self.command_id = command_id  # id which increases for each send command from the controller


class HttpServer:
    def __init__(self):
        self.webServer = HTTPServer(('', 32400), HTTPRequestHandler)

    def start(self):
        webserver_daemon = threading.Thread(name='web_daemon_server',
                                            target=self.start_webserver)
        webserver_daemon.setDaemon(True)  # Set as a daemon so it will be killed once the main thread is dead.
        webserver_daemon.start()

    def start_webserver(self):
        self.webServer.serve_forever()

    def close(self):
        self.webServer.server_close()


class HTTPRequestHandler(BaseHTTPRequestHandler):
    subscriptions = {}

    def do_GET(self):
        # libutil.DEBUG_LOG("Incoming web request at {0}".format(self.path))

        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)

        if not self.hasCorrectClientHeader():
            self.sendErrorResponse()

        if parsed_url.path == "/resources":
            self.handleResourcesRequest()
        elif parsed_url.path == "/player/timeline/subscribe":
            self.handleSubscribeRequest(parsed_url, params)
        elif parsed_url.path == "/player/timeline/unsubscribe":
            self.handleUnsubscribeRequest(parsed_url, params)
        else:
            print("no handler for {0}".format(self.path))

    def hasCorrectClientHeader(self):
        targetIdentifierHeader = self.headers.get("X-Plex-Target-Client-Identifier")
        if (not targetIdentifierHeader) or targetIdentifierHeader == util.getAttributes().get("machineIdentifier"):
            return True
        return False

    def getClientIdentifier(self):
        return self.headers.get("X-Plex-Client-Identifier")

    def addStandardHeader(self):
        identifier = util.getAttributes().get("machineIdentifier")
        self.send_header("X-Plex-Client-Identifier", identifier)

    def sendErrorResponse(self):
        self.send_response(404)
        self.addStandardHeader()
        self.end_headers()

    def handleResourcesRequest(self):
        self.send_response(200)
        self.addStandardHeader()
        self.send_header("Content-type", "application/xml")  # application/xml
        self.end_headers()

        response = self.getResourcesXML()

        self.wfile.write(response)
        print("Written response: {0}".format(response))
        # libutil.DEBUG_LOG("Answered WebServer requested {0}".format(response))

    def getResourcesXML(self):
        data = ET.Element('MediaContainer', {"size": "1"})

        attributes = util.getAttributes()
        player = ET.SubElement(data, 'Player', attributes)
        return ET.tostring(data, xml_declaration=True)

    def getTimelineXML(self, commandID):
        # TODO implement dynamic data
        data = ET.Element('MediaContainer', {
            "location": "navigation",
            "commandID": str(commandID),
            "textFieldFocused": "field"
        })
        attributes = {
            "type": "video",
            "state": "stopped",
            "controllable": "[volume,shuffle,repeat,audioStream,videoStream,subtitleStream,skipPrevious,skipNext,seekTo,stepBack,stepForward,stop,playPause]",
        }
        timeline = ET.SubElement(data, 'Timeline', attributes)
        return ET.tostring(data, xml_declaration=True)

    def handleSubscribeRequest(self, parsed_url, params):
        command_id = int(params.get("commandID")[0])
        client_ident = self.getClientIdentifier()
        subscription = self.subscriptions.get(client_ident)
        if not subscription:
            subscription = Subscription(client_ident, command_id)
            self.subscriptions[client_ident] = subscription

        self.send_response(200)
        self.addStandardHeader()
        self.send_header("Content-type", "application/xml")
        self.end_headers()

        response = self.getTimelineXML(command_id)

        self.wfile.write(response)

    def handleUnsubscribeRequest(self, parsed_url, params):
        self.subscriptions[self.getClientIdentifier()] = None  # delete subscription
        self.send_response(200)
        self.addStandardHeader()
        self.end_headers()


if __name__ == "__main__":
    gdm = GDMClientDiscovery()
    gdm.discover()
    server = HttpServer()
    server.start()

    time.sleep(30)

    gdm.close()
    server.close()
