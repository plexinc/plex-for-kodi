from __future__ import absolute_import
import threading
import socket

from . import util

DISCOVERY_PORT = 32412
WIN_NL = chr(13) + chr(10)


class GDMClientDiscovery(object):
    gdm_range = "0.0.0.0"
    gdm_port = 32412
    gdm_timeout = 10

    # TODO centralize settings
    plex_protocol_capabilities = "timeline,playback,navigation,mirror,playqueues"
    machine_identifier = "plex-kodi-plex-xxxxxx"

    def __init__(self):
        self._close = False
        self.thread = None

    def isActive(self):
        from . import plexapp
        return util.INTERFACE.getPreference("gdm_discovery", True) and self.thread and self.thread.isAlive()

    def close(self):
        self._close = True

    def discover(self):
        from . import plexapp
        if not util.INTERFACE.getPreference("gdm_discovery", True) or self.isActive():
            return

        self.thread = threading.Thread(target=self._discover)
        self.thread.start()

    def _discover(self):
        packet = ("M-SEARCH * HTTP/1.1" + WIN_NL + WIN_NL).encode("utf-8")
        response = self.getResponseString()
        # setup socket to listen to incoming gdm client searches
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.gdm_timeout)
        sock.bind((self.gdm_range, self.gdm_port))

        while not self._close:
            try:
                data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
                if data[0] == packet:
                    util.DEBUG_LOG("Received client search GDM message from {0}").format(addr[0])
                    sock.sendto(response.encode("utf-8"), addr)
                    util.DEBUG_LOG("Sent GDM client announcement to {0}").format(addr[0])
            except:
                util.ERROR()

    def getResponseString(self):
        response_string = "HTTP/1.0 200 OK" + WIN_NL
        response_string = appendNameValue(response_string, "Name", socket.gethostname())
        response_string = appendNameValue(response_string, "Port", "32400")
        response_string = appendNameValue(response_string, "Product", "Plex for Kodi")
        response_string = appendNameValue(response_string, "Content-Type", "plex/media-player")
        response_string = appendNameValue(response_string, "Protocol", "plex")
        response_string = appendNameValue(response_string, "Protocol-Version", "3")
        response_string = appendNameValue(response_string, "Protocol-Capabilities", self.plex_protocol_capabilities)
        response_string = appendNameValue(response_string, "Version", util.ADDON.getAddonInfo('version'))
        response_string = appendNameValue(response_string, "Resource-Identifier", self.machine_identifier)
        response_string = appendNameValue(response_string, "Device-Class", "stb")
        return response_string


def appendNameValue(buf, name, value):
    line = name + ": " + value + WIN_NL
    return buf + line


CLIENT_DISCOVERY = GDMClientDiscovery()
