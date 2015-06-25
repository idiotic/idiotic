from idiotic import event
import idiotic
import logging

log = logging.getLogger("idiotic.scene")

class SceneType(type):
    def __new__(cls, name, bases, attrs):
        if name.startswith('None'):
            return None

        newattrs = dict(attrs)
        if 'NAME' not in attrs:
            newattrs['NAME'] = name

        return super(SceneType, cls).__new__(cls, name, bases, newattrs)

    def __init__(self, name, bases, attrs):
        super(SceneType, self).__init__(name, bases, attrs)

        idiotic._register_scene(self.NAME, self())

class Scene:
    __metaclass__ = SceneType

    def __init__(self):
        self.__active = False

    def _switch(self, val):
        if self.__active == val:
            log.debug("Ignoring redundant scene activation for {}".format(self))
            return val

        pre_event = event.SceneEvent(self, val, "before")
        idiotic.dispatcher.dispatch(pre_event)
        if not pre_event.canceled:
            self.__active = val

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

    def __bool__(self):
        return self.__active

    def __str__(self):
        return "Scene {}".format(type(self))
