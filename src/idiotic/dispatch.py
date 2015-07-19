from idiotic.utils import Filter
from asyncio import coroutine, Queue, QueueFull
import logging
import functools

LOG = logging.getLogger("idiotic.dispatch")

class Dispatcher:
    def __init__(self):
        self.bindings = []
        self.queue = Queue()

    def bind(self, action, filt=Filter()):
        # The default filter will always return True
        self.bindings.append( (action, filt) )

    def unbind(self, action):
        for action, filt in list(self.bindings):
            self.bindings.remove( (action, filt) )
            return True
        return False

    def dispatch(self, event):
        for action in (a for a, f in self.bindings if f.check(event)):
            LOG.debug("Dispatching {}".format(str(action)))
            try:
                self.queue.put_nowait(functools.partial(action, event))
            except QueueFull:
                LOG.error("The unbounded queue is full! Pretty weird, eh?")

    @coroutine
    def run(self):
        while True:
            func = yield from self.queue.get()
            try:
                yield from coroutine(func)()
            except:
                LOG.exception("Error while running {} from dispatch queue:".format(func))
