from __future__ import absolute_import, print_function
import threading
import socket

from lib import util

DISCOVERY_PORT = 32412
WIN_NL = chr(13) + chr(10)


class GDMClientDiscovery(object):
    gdm_range = "0.0.0.0"
    gdm_port = 32412
    gdm_timeout = 10

    def __init__(self):
        self._close = False
        self.thread = None

    def isActive(self):
        #return util.getSetting(32042, True) and self.thread and self.thread.isAlive()
        # TODO replace
        return True and self.thread and self.thread.isAlive()

    def close(self):
        self._close = True

    def discover(self):
        #if not util.getSetting(32042, True) or self.isActive():
        # TODO replace
        if not True or self.isActive():
            return

        self.thread = threading.Thread(target=self._discover)
        self.thread.start()

    def _discover(self):
        packet = ("M-SEARCH * HTTP/1.1" + WIN_NL).encode("utf-8")
        response = self.getResponseString()
        # setup socket to listen to incoming gdm client searches
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.gdm_timeout)
        sock.bind((self.gdm_range, self.gdm_port))

        while not self._close:
            try:
                data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
                if data == packet:
                    # TODO replace
                    print ("Received client search GDM message from {0}".format(addr[0]))
                    #util.DEBUG_LOG("Received client search GDM message from {0}").format(addr[0])
                    sock.sendto(response.encode("utf-8"), addr)
                    # TODO replace
                    print ("Sent GDM client announcement to {0}".format(addr[0]))
                    #util.DEBUG_LOG("Sent GDM client announcement to {0}").format(addr[0])
            except:
                # TODO replace
                print("error")
                #util.ERROR()

    def getResponseString(self):
        attributes = util.getAttributes()
        response_string = "HTTP/1.0 200 OK" + WIN_NL
        response_string = appendNameValue(response_string, "Name", attributes.get("title"))
        response_string = appendNameValue(response_string, "Port", "32400")
        response_string = appendNameValue(response_string, "Product", attributes.get("product"))
        response_string = appendNameValue(response_string, "Content-Type", "plex/media-player")
        response_string = appendNameValue(response_string, "Protocol", "plex")
        response_string = appendNameValue(response_string, "Protocol-Version", "3")
        response_string = appendNameValue(response_string, "Protocol-Capabilities", attributes.get("protocolCapabilities"))
        response_string = appendNameValue(response_string, "Version", attributes.get("version"))
        response_string = appendNameValue(response_string, "Resource-Identifier", attributes.get("machineIdentifier"))
        response_string = appendNameValue(response_string, "Device-Class", "stb")
        return response_string


def appendNameValue(buf, name, value):
    line = name + ": " + value + WIN_NL
    return buf + line


if __name__ == "__main__":
    gdm = GDMClientDiscovery()
    gdm._discover()
