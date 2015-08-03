from idiotic import event, history
import idiotic
import logging

LOG = logging.getLogger("idiotic.scene")

class SceneType(type):
    def __new__(mcs, name, bases, attrs):
        if name.startswith('None'):
            return None

        newattrs = dict(attrs)
        if 'NAME' not in attrs:
            newattrs['NAME'] = name

        return super(SceneType, mcs).__new__(mcs, name, bases, newattrs)

    def __init__(cls, name, bases, attrs):
        super(SceneType, cls).__init__(name, bases, attrs)
        if name != "Scene":
            idiotic._register_scene(cls.NAME, cls())

class Scene(metaclass=SceneType):
    TAGS = set()
    def __init__(self):
        self.__active = False
        self.history = history.History()
        self.tags = self.TAGS
        self.tags.add("_scene")

    def _switch(self, val):
        if self.__active == val:
            LOG.debug("Ignoring redundant scene activation for {}".format(self))
            return val

        pre_event = event.SceneEvent(self, val, "before")
        idiotic.dispatcher.dispatch(pre_event)
        if not pre_event.canceled:
            self.__active = val

            if hasattr(self, "history"):
                self.history.record(self.__active)

            if val:
                self.entered()
            else:
                self.exited()

            post_event = event.SceneEvent(self, val, "after")
            idiotic.dispatcher.dispatch(post_event)
        return val

    def enter(self):
        return self._switch(True)

    def exit(self):
        return self._switch(False)

    def entered(self):
        pass

    def exited(self):
        pass

    @property
    def active(self):
        return self.__active

    @active.setter
    def active(self, val):
        return self._switch(bool(val))

    @property
    def name(self):
        return type(self).__name__

    def pack(self):
        return {
            "__class__": type(self).__name__,
            "__owner__": getattr(self, 'MODULE', 'unknown'),
            "__kind__": "scene",
            "__active": self.__active,
            "__methods__": [k for k, v in self.__dict__.items() if callable(v)
                            and not k.startswith('__')]
        }.update(self.__dict__)

    def __bool__(self):
        return self.__active

    def __str__(self):
        return "Scene {}".format(type(self))
