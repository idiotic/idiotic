from idiotic.event import EventFilter
from asyncio import coroutine, Queue, sleep
import logging
import functools

log = logging.getLogger("idiotic.dispatch")

class Dispatcher:
    def __init__(self):
        self.bindings = []
        self.queue = Queue()

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
            log.debug("Doing {}".format(str(action)))

            self.queue.put(functools.partial(action, event))
            log.debug("Done")

    @coroutine
    def run(self):
        while True:
            while self.queue.empty():
                yield from asyncio.sleep(.01)

            yield from self.queue.get()
