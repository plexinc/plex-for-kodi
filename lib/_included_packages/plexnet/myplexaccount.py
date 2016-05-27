import json
import time
import hashlib

import plexapp
import plexservermanager
# import plexobjects
# import plexresource


# class MyPlexAccount(plexobjects.PlexObject):
#     """ Represents myPlex account if you already have a connection to a server. """

#     def resources(self):
#         return plexresource.PlexResource.fetchResources(self.authToken)

#     def users(self):
#         import myplex
#         return myplex.MyPlexHomeUser.fetchUsers(self.authToken)

#     def getResource(self, search, port=32400):
#         """ Searches server.name, server.sourceTitle and server.host:server.port
#             from the list of available for this PlexAccount.
#         """
#         return plexresource.findResource(self.resources(), search, port)

#     def getResourceByID(self, ID):
#         """ Searches by server.clientIdentifier
#             from the list of available for this PlexAccount.
#         """
#         return plexresource.findResourceByID(self.resources(), ID)


class MyPlexAccount(object):
    def __init__(self):
        # Strings
        self.ID = None
        self.title = None
        self.username = None
        self.email = None
        self.authToken = None

        # Booleans
        self.isAuthenticated = plexapp.getPreference('auto_signin', False)
        self.isSignedIn = False
        self.isOffline = False
        self.isExpired = False
        self.isPlexPass = False
        self.isManaged = False
        self.isSecure = False
        self.hasQueue = False

        self.homeUsers = []

        self.loadState()

    def saveState(self):
        obj = {
            'ID': self.ID,
            'title': self.title,
            'username': self.username,
            'email': self.email,
            'authToken': self.authToken,
            'pin': self.pin,
            'isPlexPass': self.isPlexPass,
            'isManaged': self.isManaged,
            'isAdmin': self.isAdmin,
            'isSecure': self.isSecure,
        }

        plexapp.INTERFACE.setRegistry("MyPlexAccount", json.dumps(obj), "myplex")

    def loadState(self):
        # Look for the new JSON serialization. If it's not there, look for the
        # old token and Plex Pass values.

        plexapp.INTERFACE.addInitializer("myplex")
        settings = AppSettings()

        json = plexapp.INTERFACE.getRegistry("MyPlexAccount", None, "myplex")

        if json:
            obj = json.loads(json)
            if obj:
                self.ID = obj.get('ID') or self.ID
                self.title = obj.get('title') or self.title
                self.username = obj.get('username') or self.username
                self.email = obj.get('email') or self.email
                self.authToken = obj.get('authToken') or self.authToken
                self.pin = obj.get('pin') or self.pin
                self.isPlexPass = obj.get('isPlexPass') or self.isPlexPass
                self.isManaged = obj.get('isManaged') or self.isManaged
                self.isAdmin = obj.get('isAdmin') or self.isAdmin
                self.isSecure = obj.get('isSecure') or self.isSecure
                self.isProtected = bool(obj.get('pin'))

        if self.authToken:  # TODO: -------------------------------------------------------------------------------------------------------------------IMPLEMENT
            request = createMyPlexRequest("/users/account")
            context = request.CreateRequestContext("account", createCallable("OnAccountResponse", m))
            context.timeout = 10000
            Application().StartRequest(request, context)
        else:
            plexapp.INTERFACE.clearInitializer("myplex")

    def onAccountResponse(request, response, context):
        oldId = self.ID

        if response.isSuccess():
            xml = response.GetBodyXml()

            # The user is signed in
            self.isSignedIn = True
            self.isOffline = False
            self.ID = xml@id
            self.title = xml@title
            self.username = xml@username
            self.email = xml@email
            self.thumb = xml@thumb
            self.authToken = xml@authenticationToken
            self.isPlexPass = (xml.subscription <> invalid and xml.subscription@active = "1")
            self.isManaged = (xml@restricted = "1")
            self.isSecure = (xml@secure = "1")
            self.hasQueue = (xml@queueEmail <> invalid and xml@queueEmail <> "" and xml@queueEmail <> invalid and xml@queueEmail <> "")

            # PIN
            if xml@pin <> invalid and xml@pin <> "":
                self.pin = xml@pin
            else:
                self.pin = invalid
            self.isProtected = (m.pin <> invalid)

            # update the list of users in the home
            self.UpdateHomeUsers()

            # set admin attribute for the user
            self.isAdmin = False
            if self.homeUsers.count() > 0 then
                for each user in self.homeUsers
                    if self.ID = user.ID then
                        self.isAdmin = (tostr(user.admin) = "1")
                        break

            # consider a single, unprotected user authenticated
            if self.isAuthenticated = False and self.isProtected = False and self.homeUsers.Count() <= 1 then
                self.isAuthenticated = True

            Info("Authenticated as " + tostr(m.ID) + ":" + tostr(m.Title))
            Info("SignedIn: " + tostr(m.isSignedIn))
            Info("Offline: " + tostr(m.isOffline))
            Info("Authenticated: " + tostr(m.isAuthenticated))
            Info("PlexPass: " + tostr(m.isPlexPass))
            Info("Managed: " + tostr(m.isManaged))
            Info("Protected: " + tostr(m.isProtected))
            Info("Admin: " + tostr(m.isAdmin))

            self.SaveState()
            MyPlexManager().Publish()
            RefreshResources()
        else if response.GetStatus() >= 400 and response.GetStatus() < 500 then
            # The user is specifically unauthorized, clear everything
            Warn("Sign Out: User is unauthorized")
            self.SignOut(True)
        else
            # Unexpected error, keep using whatever we read from the registry
            Warn("Unexpected response from plex.tv (" + tostr(response.GetStatus()) + "), switching to offline mode")
            self.isOffline = True
            # consider a single, unprotected user authenticated
            if self.isAuthenticated = False and self.isProtected = False then
                self.isAuthenticated = True
            end if
        end if

        Application().ClearInitializer("myplex")
        Logger().UpdateSyslogHeader()

        if oldId <> self.ID or self.switchUser = True then
            self.switchUser = invalid
            Application().Trigger("change:user", [m, (oldId <> self.ID)])
        end if

    def signOut(expired=False):
        # Strings
        self.ID = None
        self.title = None
        self.username = None
        self.email = None
        self.authToken = None
        self.pin = None
        self.lastHomeUserUpdate = None

        # Booleans
        self.isSignedIn = False
        self.isPlexPass = False
        self.isManaged = False
        self.isSecure = False
        self.isExpired = expired

        # Clear the saved resources
        plexapp.INTERFACE.clearRegistry("mpaResources", "xml_cache")

        # Remove all saved servers
        plexservermanager.MANAGER.clearServers()

        # Enable the welcome screen again
        plexapp.INTERFACE.setPreference("show_welcome", True)

        plexapp.INTERFACE.trigger("change:user", [self, True])

        self.saveState()

    def validateToken(self, token, switchUser=False):
        self.authToken = token
        self.switchUser = switchUser

        # TODO: --------------------------------------------------------------------------------------------------------------------------------------IMPLEMENT
        request = createMyPlexRequest("/users/sign_in.xml")
        context = request.CreateRequestContext("sign_in", createCallable("OnAccountResponse", m))
        context.timeout = iif(m.isOffline, 1000, 10000)
        Application().StartRequest(request, context, "")

    def updateHomeUsers(self):
        # Ignore request and clear any home users we are not signed in
        if not self.isSignedIn:
            self.homeUsers = []
            if self.isOffline:
                self.homeUsers.append(MyPlexAccount())  # TODO: ---------------------------------------------------------------------------------------IMPLEMENT

            self.lastHomeUserUpdate = None
            return

        # Cache home users for 60 seconds, mainly to stop back to back tests
        epoch = time.time()
        if not self.lastHomeUserUpdate:
            self.lastHomeUserUpdate = epoch
        elif self.lastHomeUserUpdate + 60 > epoch:
            util.DEBUG_LOG("Skipping home user update (updated {0} seconds ago)".format(epoch - self.lastHomeUserUpdate))
            return

        req = createMyPlexRequest("/api/home/users")
        xml = CreateObject("roXMLElement")
        xml.Parse(req.GetToStringWithTimeout(10))
        if int(xml@size or "0") and xml.user:
            self.homeUsers = []
            for user in xml.user:
                homeUser = user.GetAttributes()
                homeUser.isAdmin = (homeUser.admin = "1")
                homeUser.isManaged = (homeUser.restricted = "1")
                homeUser.isProtected = (homeUser.protected = "1")
                self.homeUsers.append(homeUser)

            self.lastHomeUserUpdate = epoch

        util.LOG("home users: {0}".format(len(m.homeUsers.count)))

    def switchHomeUser(self, userId, pin=''):
        if userId = self.ID and self.isAuthenticated:
            return True

        # Offline support
        if self.isOffline:
            digest = hashlib.sha256()
            digest.update(pin + self.AuthToken)
            if not self.isProtected or self.isAuthenticated or digest.digest() == (self.pin or ""):
                util.DEBUG_LOG("Offline access granted")
                self.isAuthenticated = True
                self.validateToken(self.AuthToken, True)
                return True
        else:
            # TODO: -----------------------------------------------------------------------------------------------------------------------------------IMPLEMENT
            # build path and post to myplex to swith the user
            path = "/api/home/users/" + userid + "/switch"
            req = createMyPlexRequest(path)
            xml = CreateObject("roXMLElement")
            xml.Parse(req.PostToStringWithTimeout("pin=" + pin, 10))

            if xml@authenticationToken:
                self.isAuthenticated = True
                # validate the token (trigger change:user) on user change or channel startup
                if userId != self.ID or not Locks().IsLocked("idleLock"):
                    self.ValidateToken(xml@authenticationToken, True)
                return True

        return False

    def isActive(self):
        return self.isSignedIn or self.isOffline
