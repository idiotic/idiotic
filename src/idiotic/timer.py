import asyncio

class Timer:
    def __init__(self, delay, func, *args, **kwargs):
        self.started = False
        self.completed = False
        self.canceled = False

        self.delay = delay

        self.func = func
        self.args = args
        self.kwargs = kwargs

        self.__handle = None

    def start(self):
        self.reschedule()

    def reschedule(self, delay=None):
        if delay is None:
            delay = self.delay
        else:
            self.delay = delay

        self.cancel()

        self.completed = False
        self.canceled = False
        self.__handle = asyncio.get_event_loop().call_later(delay, self.__run)
        self.started = True

    def __run(self):
        if not self.canceled:
            self.func(*self.args, **self.kwargs)
            self.completed = True

    def cancel(self):
        self.canceled = True
        if self.__handle != None:
            self.__handle.cancel()
