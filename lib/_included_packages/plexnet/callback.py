import threading


class Callable(object):
    _currID = 0

    def __init__(self, func, context=None, forcedArgs=None, ID=None):
        self.func = func
        self.context = context
        self.forcedArgs = forcedArgs

        if not context:
            self.ID = ID
        else:
            self.ID = ID or id(func)

        if not self.ID:
            self.id = Callable.nextID()

    def __eq__(self, other):
        if not other:
            return False

        if self.__class__ != other.__class__:
            return False

        return self.id and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __call__(self, *args):
        args = args or []
        if self.forcedArgs:
            args = self.forcedArgs

        self.func(*args)

    @classmethod
    def nextID(cls):
        cls._currID += 1
        return cls._currID

    def callableDeferCall(self, timeout=100):
        timer = threading.Timer(timeout, self.onDeferCallTimer)
        timer.start()

    def onDeferCallTimer(self):
        self()
