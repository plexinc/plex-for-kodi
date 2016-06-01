import signalslot


class SignalsMixin(object):
    def __init__(self):
        self.signals = {}

    def on(self, signalName, callback):
        if signalName not in self.signals:
            self.signals[signalName] = signalslot.Signal(threadsafe=True)

        signal = self.signals[signalName]

        signal.connect(callback)

    def off(self, signalName, callback):
        if not self.signals:
            return

        if not signalName:
            if not callback:
                self.signals = {}
            else:
                for name in self.signals:
                    self.off(name, callback)
        else:
            if not callback:
                if signalName in self.signals:
                    del self.signals[signalName]
            else:
                self.signals[signalName].disconnect(callback)

    def trigger(self, signalName, **kwargs):
        if not self.signals:
            return

        if signalName not in self.signals:
            return

        self.signals[signalName].emit(**kwargs)
