import plexobjects
import plexresource


class MyPlexAccount(plexobjects.PlexObject):
    """ Represents myPlex account if you already have a connection to a server. """

    def resources(self):
        return plexresource.PlexResource.fetchResources(self.authToken)

    def users(self):
        import myplex
        return myplex.MyPlexHomeUser.fetchUsers(self.authToken)

    def getResource(self, search, port=32400):
        """ Searches server.name, server.sourceTitle and server.host:server.port
            from the list of available for this PlexAccount.
        """
        return plexresource.findResource(self.resources(), search, port)

    def getResourceByID(self, ID):
        """ Searches by server.clientIdentifier
            from the list of available for this PlexAccount.
        """
        return plexresource.findResourceByID(self.resources(), ID)
