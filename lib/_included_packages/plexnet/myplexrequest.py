# We don't particularly need a class definition here (yet?), it's just a
# PlexRequest where the server is fixed.
from __future__ import absolute_import
from . import plexrequest


class MyPlexRequest(plexrequest.PlexServerRequest):
    def __init__(self, path):
        from . import myplexserver
        plexrequest.PlexServerRequest.__init__(self, myplexserver.MyPlexServer(), path)

        # Make sure we're always getting XML
        self.addHeader("Accept", "application/xml")
