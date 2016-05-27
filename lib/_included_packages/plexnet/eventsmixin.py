class EventsMixin(object):
    def on(self, eventName, callback):
        self.eventsCallbacks = self.eventsCallbacks or {}

        callbacks = self.eventsCallbacks[eventName]
        if not callbacks:
            callbacks = []
            self.eventsCallbacks[eventName] = callbacks

        # If the callback has an ID, check for duplicates
        if callback.id:
            if callback in callbacks:
                return

        callbacks.append(callback)

    def off(self, eventName, callback):
        if not self.eventsCallbacks:
            return

        if not eventName:
            if not callback:
                self.eventsCallbacks = None
            elif callback.id:
                for name in self.eventsCallbacks:
                    self.off(name, callback)
        else:
            if not callback:
                if eventName in self.eventsCallbacks:
                    del self.eventsCallbacks[eventName]
            elif callback.id:
                callbacks = self.eventsCallbacks[eventName]
                if not callbacks:
                    return

                if callback in callbacks:
                    del callbacks[callbacks.index(callback)]

    def trigger(self, eventName, args=None):
        args = args or []
        if not self.eventsCallbacks:
            return

        callbacks = self.eventsCallbacks[eventName]
        if not callbacks:
            return

        for callback in callbacks:
            callback(*args)
