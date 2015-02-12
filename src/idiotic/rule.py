import idiotic

def bind(func=None, *events):
    if len(events) == 0:
        events = [func]
        func = None

    if func:
        for event in events:
            event.bind(func)

            if not hasattr(func, "_rule_triggers"):
                func._rule_triggers = []
        func._rule_triggers.extend(list(events))
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
            self.item.bind_on_command(callback)
        elif not self.commands:
            self.item.bind_on_command(callback, kind=self.time)
        elif not self.time:
            self.item.bind_on_command(callback, command__in=self.commands)
        else:
            self.item.bind_on_command(callback, command__in=self.commands, kind=self.time)

class Change(EventBinder):
    def __init__(self, item, old=None, new=None, time="after"):
        self.item = item
        self.old = old
        self.new = new
        self.time = time

    def bind(self, callback):
        kw = {}
        if self.old:
            kw['old'] = self.old
        if self.new:
            kw['new'] = self.new
        if self.time != "both":
            kw['kind'] = self.time
        self.item.bind_on_change(callback, **kw)

class Schedule(EventBinder):
    """A class for binding rules to cron-like schedules.

    This uses the schedule module to provide human-readable scheduling
    syntax.

    """
    def __init__(self, schedule):
        self.schedule = schedule

    def bind(self, callback):
        self.schedule.do(callback)
        #idiotic.scheduler.bind_to_schedule(schedule, callback)
