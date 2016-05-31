import util


class GDMDiscovery(object):
    def isActive(self):
        util.LOG('GDMDiscovery().isActive() - NOT IMPLEMENTED')
        return False

    def discover(self):
        util.LOG('GDMDiscovery().discover() - NOT IMPLEMENTED')


DISCOVERY = GDMDiscovery()
