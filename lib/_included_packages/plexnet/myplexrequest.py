# We don't particularly need a class definition here (yet?), it's just a
# PlexRequest where the server is fixed.
import plexrequest


class MyPlexRequest(plexrequest.PlexRequest):
    def __init__(self, path):
        import myplexserver
        plexrequest.PlexRequest.__init__(self, myplexserver.MyPlexServer(), path)

        # Make sure we're always getting XML
        self.addHeader("Accept", "application/xml")
