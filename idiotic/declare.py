import functools
import asyncio
import idiotic
import logging
import datetime

LOG = logging.getLogger("idiotic.declare")

class Condition:
    def __init__(self, parent=None):
        self.parent = parent
        self.__state = None
        self.__set = False

    @property
    def state(self):
        if not self.__set:
            self.recalculate()
            self.__set = True

        return self.__state

    def set_as_parent(self, *children):
        for c in children:
            c.parent = self

    def child_changed(self, child, status):
        self.recalculate()

    def recalculate(self, *_, **__):
        new_state = self.calculate()
        if new_state != self.__state:
            self.__state = new_state

            if self.parent:
                self.parent.child_changed(self, self.state)

    def calculate(self):
        return False

    def __and__(self, other):
        return AndCondition(self, other)

    def __or__(self, other):
        return OrCondition(self, other)

    def __neg__(self):
        return NotCondition(self)

    def __invert__(self):
        return NotCondition(self)

    def __xor__(self, other):
        return XorCondition(self, other)

class AndCondition(Condition):
    def __init__(self, *children, **kwargs):
        super().__init__(**kwargs)
        self.children = children
        self.set_as_parent(*children)

    def calculate(self):
        return all((c.state for c in self.children))

class OrCondition(Condition):
    def __init__(self, *children, **kwargs):
        super().__init__(**kwargs)
        self.children = children
        self.set_as_parent(*children)

    def calculate(self):
        return any((c.state for c in self.children))

class XorCondition(Condition):
    def __init__(self, p, q, **kwargs):
        super().__init__(**kwargs)
        self.p = p
        self.q = q
        self.set_as_parent(p, q)

    def calculate(self):
        return self.p.state != self.q.state

class NotCondition(Condition):
    def __init__(self, child, **kwargs):
        super().__init__(**kwargs)
        self.child = child
        self.child.parent = self

    def calculate(self):
        return not self.child.state

class StateIsCondition(Condition):
    def __init__(self, item, state, **kwargs):
        super().__init__(**kwargs)
        # TODO: Add support for [state-has-been-x-for-duration] [within-x-time-ago]

        self.item = item
        self.target_state = state

        self.item.bind_on_change(self.recalculate)

    def calculate(self):
        return self.item.state == self.target_state

class Action:
    def __init__(self):
        raise NotImplementedError()

class SceneAction(Action):
    def __init__(self, scene, invert=False):
        self.scene = scene
        self.invert = invert
    
class Rule:
    def __init__(self, condition, both=None, yes=None, no=None):
        self.condition = condition
        self.both = both
        self.yes = yes
        self.no = no

        self.condition.parent = self

    def __dispatch_func(self, funcs, status, include_status):
        if isinstance(funcs, Action):
            raise NotImplementedError()
        if callable(funcs):
            if include_status:
                funcs(status)
            else:
                funcs()
        else:
            for func in funcs:
                self.__dispatch_func(func, status, include_status)

    def child_changed(self, child, status):
        if self.both:
            self.__dispatch_func(self.both, status, True)

        if status and self.yes:
            self.__dispatch_func(self.yes, status, False)
        elif not status and self.no:
            self.__dispatch_func(self.no, status, False)
