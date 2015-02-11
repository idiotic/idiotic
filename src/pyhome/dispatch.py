from pyhome.event import EventFilter

class Dispatcher:
    def __init__(self):
        self.bindings = []

    def bind(self, action, filt=EventFilter()):
        # The default event filter will always return True
        self.bindings.append( (action, filt) )

    def unbind(self, action):
        for action, filt in list(self.bindings):
            self.bindings.remove( (action, filt) )
            return True
        return False

    def dispatch(self, event):
        for action in (a for a, f in self.bindings if f.check(event)):
            action(event)
