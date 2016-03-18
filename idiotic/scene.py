from idiotic import event, history
import idiotic
import logging

LOG = logging.getLogger("idiotic.scene")

class Scene:
    def __init__(self, name, active={}, inactive={}, tags=()):
        self.name = name
        self.history = history.History()
        self._active_state = dict(active)
        self._inactive_state = dict(inactive)
        self.tags = set(tags)
        self.tags.add("_scene")

        self.__active = False

        self._on_enter_funcs = []
        self._on_exit_funcs = []

        idiotic._register_scene(name, self)

    def _switch(self, val):
        if self.__active == val:
            LOG.debug("Ignoring redundant scene activation for {}".format(self))
            return

        pre_event = event.SceneEvent(self, val, "before")
        self.idiotic.dispatcher.dispatch(pre_event)
        if not pre_event.canceled:
            self.__active = val

            if hasattr(self, "history"):
                self.history.record(self.__active)

            if val:
                self._activate()
                for f in self._on_enter_funcs:
                    try:
                        f()
                    except:
                        pass
            else:
                self._deactivate()
                for f in self._on_exit_funcs:
                    try:
                        f()
                    except:
                        pass

            post_event = event.SceneEvent(self, val, "after")
            self.idiotic.dispatcher.dispatch(post_event)
        return val

    def _activate(self):
        itag = "_scene_" + self.name + "_inactive"
        atag = "_scene_" + self.name + "_active"
        for name in self._inactive_state.keys():
            try:
                item = self.idiotic.items[name]
                item.remove_state_overlay(tag=itag)
            except NameError:
                pass

        for name, state in self._active_state.items():
            try:
                item = self.idiotic.items[name]
                if isinstance(state, tuple):
                    state, disable = state
                else:
                    disable = False
                item.overlay_state(state, tag=atag, disable=disable)
            except NameError:
                pass

    def _deactivate(self):
        itag = "_scene_" + self.name + "_inactive"
        atag = "_scene_" + self.name + "_active"
        for name in self._active_state.keys():
            try:
                item = self.idiotic.items[name]
                item.remove_state_overlay(tag=atag)
            except NameError:
                pass

        for name, state in self._inactive_state.items():
            try:
                item = self.idiotic.items[name]
                if isinstance(state, tuple):
                    state, disable = state
                else:
                    disable = False
                item.overlay_state(state, tag=itag, disable=disable)
            except NameError:
                pass

    def enter(self):
        return self._switch(True)

    def exit(self):
        return self._switch(False)

    def on_exit(self, func):
        self._on_exit_funcs.append(func)
        return func

    def on_enter(self, func):
        self._on_enter_funcs.append(func)
        return func

    @property
    def active(self):
        return self.__active

    @active.setter
    def active(self, val):
        return self._switch(bool(val))

    def pack(self):
        result = {
            "__class__": type(self).__name__,
            "__owner__": getattr(self, 'MODULE', 'unknown'),
            "__kind__": "scene",
            "__active": self.__active,
            "__methods__": [k for k, v in self.__dict__.items() if callable(v)
                            and not k.startswith('__')]
        }
        result.update(self.__dict__)
        return result

    def json(self):
        return {
            "type": "Scene",
            "name": self.name,
            "active": self.__active,
            "tags": list(self.tags),
        }

    def __bool__(self):
        return self.__active

    def __str__(self):
        return "Scene {}".format(self.name)
