import logging
import idiotic
from idiotic import event, modules

log = logging.getLogger("idiotic.item")

def command(func):
    def decorator(self, *args, **kwargs):
        # If we get passed a source (e.g., UI, Rule, Binding), consume
        # it so we don't break our child function
        if "source" in kwargs:
            source = kwargs["source"]
            del kwargs["source"]
        else:
            source = None

        if "command" in kwargs:
            command = kwargs["command"]
        else:
            command = func.__name__

        # Create an event and send it 
        pre_event = event.CommandEvent(self, command, source, kind="before")
        idiotic.dispatcher.dispatch(pre_event)

        if not pre_event.canceled:
            func(self, *args, **kwargs)
            post_event = event.CommandEvent(self, command, source, kind="after")
            idiotic.dispatcher.dispatch(post_event)
    return decorator

class BaseItem:
    """The base class for an item which implements all the basic
    behind-the-scenes functionality and makes no assumptions about the
    nature of its state.

    """
    def __init__(self, name, groups=None, friends=None, bindings=None):
        self.name = name
        self._state = None
        if friends is None:
            self.friends = {}
        else:
            self.friends = friends

        if groups is None:
            self.groups = set()
        else:
            self.groups = set(groups)

        idiotic._register_item(self)

        if bindings:
            for module_name, args in bindings.items():
                log.debug("Setting {} bindings on {}".format(module_name, self))
                module = getattr(modules, module_name)
                module.bind_item(self, **args)

    def bind_on_command(self, function, **kwargs):
        idiotic.dispatcher.bind(function, event.EventFilter(type=event.CommandEvent, item=self, **kwargs))

    def bind_on_change(self, function, **kwargs):
        idiotic.dispatcher.bind(function, event.EventFilter(type=event.StateChangeEvent, item=self, **kwargs))

    def __str__(self):
        return type(self).__name__ + " '" + self.name + "'"

    def __repr__(self):
        return type(self).__name__ + " '" + self.name + "' on local"

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._set_state_from_context(state)

    def _set_state_from_context(self, val, source="rule"):
        # We don't send an event if there has been literally no change
        if self._state == val:
            log.debug("Ignoring redundant state change for {}".format(self))
            return

        old = self._state
        pre_event = event.StateChangeEvent(self, old, val, source, kind="before")
        idiotic.dispatcher.dispatch(pre_event)
        if not pre_event.canceled:
            self._state = val
            post_event = event.StateChangeEvent(self, old, val, source, kind="after")
            idiotic.dispatcher.dispatch(post_event)

class Switch(BaseItem):
    """An item which has two discrete states between which it may be
    toggled, and which is not affected by repeated identical commands.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command
    def on(self):
        self.state = True

    @command
    def off(self):
        self.state = False

    def toggle(self, *args, **kwargs):
        if self.state:
            self.off(*args, **kwargs)
        else:
            self.on(*args, **kwargs)

class Trigger(BaseItem):
    """An item with no state, but which may be activated repeatedly,
    triggering a distinct command each time.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command
    def activate(self):
        pass

class Number(BaseItem):
    """An item which represents a numerical quantity of some sort."""

    def __init__(self, *args, kind=float, **kwargs):
        self.kind = kind
        super().__init__(*args, **kwargs)

    @command
    def set(self, val):
        try:
            self.state = self.kind(val)
        except (ValueError, TypeError) as e:
            log.warn("Invalid {} argument to Number.set: {}".format(self.kind.__name__, val))

class _BagOfHolding:
    def __contains__(self, arg):
        return True

class _Sieve:
    def __contains__(self, arg):
        return False

class _ImposterDict:
    def __init__(self, item):
        self.item = item

    def __contains__(self, arg):
        return True

    def __getitem__(self, index):
        return self.item

class Group(BaseItem):
    """An item which contains other items. It may have custom behavior
    defined to facilitate acting on all its members at once, and to
    summarize its state.

    """
    def __init__(self, *args, state=any, state_set=None, commands=False, command_send=False, **kwargs):
        """Initialize a Group item, which may or may not handle state updates
        and commands in a custom manner.

        Keyword Arguents:
        state      -- A function which will be used to compute the
                      group's state. It should accept an iterable of
                      BaseItems and return the state. The default is
                      the builtin `any`. If set to `None`, the group
                      will have its own state, indepedent of that
                      of its members.
        state_set  -- A function which will be called when the state
                      of the group is set. It should accept an
                      iterable of BaseItems, and the new state value.
                      This is generally used to set the state of a
                      group's members by changing only the group's
                      state. By default, will do nothing. This
                      argument will be ignored if the 'state'
                      argument is `None`.
        commands   -- How to handle commands sent to the group's
                      members. If `True`, all commands on members of
                      the group will also be sent to the group. If
                      `False`, the group will only receive its own
                      commands. If this argument is an iterable, only
                      commands named by its elements will be passed on
                      to the group, and all others will be ignored.
                      Defaults to `False`.
        command_send -How to handle commands sent to the group itself.
                      If False, commands sent to the group will have
                      no effect. If this is a callable, it will be
                      passed an iterable of BaseItems, the name of the
                      command, and any arguments the command may
                      take. If this is a dictionary, the keys should
                      correspond to command names, while the values
                      are callables for which the commands will be
                      called. The function will be called in the same
                      manner as described previously. Otherwise, this
                      may be set to `True` to automatically call the
                      command on all members of the group.

        """
        super().__init__(*args, **kwargs)

        self.members = []

        self._group_state_getter = state
        self._group_state_setter = state_set

        if commands:
            try:
                self.relay_commands = set(commands)
            except TypeError:
                # 
                self.relay_commands = _BagOfHolding()
        else:
            self.relay_commands = _Sieve()

        if command_send:
            if command_send is True:
                self.send_commands = _ImposterDict(lambda items, command, *args, **kwargs: (getattr(item, command)(command=command, *args, **kwargs) for item in items))
            elif command_send is False:
                self.send_commands = _Sieve()
            elif callable(command_send):
                self.send_commands = _ImposterDict(command_send)
            elif command_send is not None:
                self.send_commansd = dict(command_send)

        @property
        def state(self):
            if self._group_state_getter:
                return self._group_state_getter(self.members)
            else:
                return super().state

        @state.setter
        def state(self, state):
            if self._group_state_setter:
                self._group_state_setter(self.members, state)
            else:
                # FIXME not sure if this will work
                super().state = state

        @command
        def command(self, command=None, *args, **kwargs):
            # Will receive any command by name
            if command and command in self.relay_commands:
                self.relay_commands[command](command, *args, **kwargs)

        def flattened(self, include_groups=False):
            """Return this group's members and all members of its subgroups, as a
            single list.

            Keyword arguments:
            include_groups    -- If True, include each subgroup along with its
                                 members. Otherwise, subgroups will not be
                                 included but their members will be.
            """
            for item in self.members:
                if type(item) is Group:
                    if include_subgroups:
                        yield item
                    yield from item.flattened(include_groups)
                else:
                    yield item

        def add(self, item):
            if item not in self.members:
                self.members.append(item)
