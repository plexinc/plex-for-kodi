from BaseHTTPServer import BaseHTTPRequestHandler

from lxml import etree as ET


class HttpServer:
    def start(self):
        print()
        # TODO implement

    def close(self):
        print()
        # TODO implement


class GDMAdvertiserRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/xml")  # application/xml
        self.end_headers()

        response = self.getWebserverResponse()

        self.wfile.write(response)
        print("WebServer requested")

    def getWebserverResponse(self):
        data = ET.Element('MediaContainer', {"size": "1"})

        # TODO unify attributes with gdm
        attributes = {
            "title": application_name,
            "machineIdentifier": machine_identifier,
            "product": plex_product,
            "version": version,
            "platform": platform,
            "platformVersion": platform_version,
            "protocolVersion": plex_protocol_version,
            "protocolCapabilities": plex_protocol_capabilities,
            "deviceClass": device_class
        }
        player = ET.SubElement(data, 'Player', attributes)
        return ET.tostring(data, xml_declaration=True)
