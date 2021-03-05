from __future__ import print_function

import threading
import time
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from lxml import etree as ET

from lib import util
from gdmClient import GDMClientDiscovery


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
    def handleResourcesRequest(self):
        self.send_response(200)
        self.send_header("Content-type", "application/xml")  # application/xml
        self.end_headers()

        response = self.getWebserverResponse()

        self.wfile.write(response)
        #libutil.DEBUG_LOG("Answered WebServer requested {0}".format(response))

    def getWebserverResponse(self):
        data = ET.Element('MediaContainer', {"size": "1"})

        attributes = util.getAttributes()
        player = ET.SubElement(data, 'Player', attributes)
        return ET.tostring(data, xml_declaration=True)

    def do_GET(self):
        #libutil.DEBUG_LOG("Incoming web request at {0}".format(self.path))
        if self.path == "/resources":
            self.handleResourcesRequest()
        else:
            print("no handler for {0}".format(self.path))


if __name__ == "__main__":
    gdm = GDMClientDiscovery()
    gdm.discover()
    server = HttpServer()
    server.start()

    time.sleep(30)

    server.close()
