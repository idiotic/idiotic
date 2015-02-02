import pyhome

def bind(func=None, *events):
    if func:
        for event in events:
            event.bind(func)

        if not hasattr(func, "_rule_triggers"):
            func._rule_triggers = []
        func._rule_triggers.extend(event)
        return func
    else:
        def partial(func):
            return bind(func, *events)
        return partial

class EventBinder:
    def bind(self, callback):
        raise NotImplemented("You must override EventBinder.bind()")

class Command(EventBinder):
    def __init__(self, item, command=None, time="after"):
        self.item = item
        if command:
            try:
                self.commands = list(command)
            except TypeError:
                self.commands = [command]
        else:
            self.commands = None

        if not time:
            time = "after"

        if time != "after" and time != "before" and time != "both":
            raise ValueError("argument 'time' to Command() must be either 'after', 'before', or 'both'")
        self.time = time

    def bind(self, callback):
        if self.commands is None and self.time == "both":
            self.item.bind_on_command(None, callback)
        else:
            def wrapper(event, *args, **kwargs):
                if self.time == "both" or event.kind == self.time:
                    if self.commands is None or event.command in self.commands:
                        callback(event, *args, **kwargs)
            if self.commands is None:
                self.item.bind_on_command(None, wrapper)
            else:
                for cmd in self.commands:
                    self.item.bind_on_command(cmd, wrapper)

class Change(EventBinder):
    def __init__(self, item, old=None, new=None, time="after"):
        self.item = item
        self.old = old
        self.new = new

    def bind(self, callback):
        def wrapper(event, *args, **kwargs):
            if self.time == "both" or self.time == event.kind:
                if self.old is None or self.old == event.old:
                    if self.new is None or self.new == event.new:
                        callback(event, *args, **kwargs)
        self.item.bind_on_change(wrapper)

class Schedule(EventBinder):
    """A class for binding rules to cron-like schedules.

    This uses the schedule module to provide human-readable scheduling
    syntax.

    """
    def __init__(self, schedule):
        self.schedule = schedule
        
    def bind(self, callback):
        pyhome.scheduler.bind_to_schedule(schedule, callback)
