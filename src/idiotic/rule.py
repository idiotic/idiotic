import asyncio
import idiotic
import logging
import datetime
from schedule import CancelJob
LOG = logging.getLogger("idiotic.rule")

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

def augment(func=None, augmentation=None):
    if not augmentation:
        augmentation = func
        func = None

    if func:
        if not hasattr(func, "_rule_augments"):
            func._rule_augments = []

        func._rule_augments.append(augmentation)
        return augmentation.wrap(func)
    else:
        def partial(func):
            return augment(func, augmentation)
        return partial

class EventBinder:
    def bind(self, callback):
        raise NotImplementedError("You must override EventBinder.bind()")

    def get_filter(self, callback):
        raise NotImplementedError("You must override EventBinder.get_filter()")

class Command(EventBinder):
    def __init__(self, item, command=None, time="after"):
        self.item = item
        if command:
            if isinstance(command, str):
                # Stupid strings and their also-being-iterable
                self.commands = [command]
            else:
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

    def get_filter(self):
        kw = {}
        if self.commands is None and self.time == "both":
            pass
        elif not self.commands:
            kw["kind"] = self.time
        elif not self.time:
            kw["command__in"] = self.commands
        else:
            kw["command__in"] = self.commands
            kw["kind"] = self.time

        return idiotic.utils.Filter(type=idiotic.event.CommandEvent, **kw)

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

    def get_filter(self):
        kw = {}
        if self.old:
            kw['old'] = self.old
        if self.new:
            kw['new'] = self.new
        if self.time != "both":
            kw['kind'] = self.time
        return idiotic.utils.Filter(type=idiotic.event.StateChangeEvent, item=self.item, **kw)

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
        self.schedule.do(lambda: callback(None))
        #idiotic.scheduler.bind_to_schedule(schedule, callback)

    def get_filter(self):
        raise NotImplementedError("get_filter() is not supported on Schedule")

class EventAugmentation:
    def wrap(func):
        raise NotImplementedError("You must override EventAugmentation.wrap()")

class Delay(EventAugmentation):
    def __init__(self, binder, period=None, cancel=False, reset=True, consume=None):
        """Initialize a rule augmentation that delays the execution of a rule
when receives certain commands.

        Arguments:
        binder -- An EventBinder which determines when the rule will be
                  delayed. Any events which match this binder will be
                  delayed by period seconds before being sent to the rule.

        Keyword arguments:
        period -- How long, in seconds, to delay the event when binder is
                  matched.
        cancel -- When to cancel the pending event timer. If True, cancels
                  when any event other than binder is received. If False,
                  never cancels the pending event when it has started. If
                  an iterable of EventBinder, will cancel when any event
                  it contains is matched. If an EventBinder, will cancel
                  when an event matches it.
        reset --  When to reset the pending event timer, if it has not yet
                  completed running. By default, will reset when the event
                  received matches binder. If set to False, will never
                  reset the timer. If set to an iterable of EventBinder,
                  will reset when any event it contains is matched. If an
                  EventBinder, will reset when an event matches it.
        consume-- When to consume an event without passing it along to the
                  rule. This is distinct from cancel in that it will send
                  an event twice if it was delayed without being consumed.
                  This will only apply to events which were also matched
                  by binder or reset.

        Example:
        The most common use case for this augmentation is for preventing
        outputs from changing state rapidly when an input changes state.
        This is especially useful for something like a motion-sensor
        which controls a light. The following augmentation will delay
        responses to the "OFF" command of "motion_sensor" for 5 minutes,
        cancel the timer when the "ON" command is received, and reset the
        timer when the "OFF" command is received (if the timer is already
        running).
            Delay(Command(items.motion_sensor, "OFF"), period=300,
                          cancel=Command(items.motion_sensor, "ON"))
        """
        if binder != True and binder != False:
            self.filt = [binder.get_filter()] if isinstance(binder, EventBinder) else [b.get_filter() for b in binder]

        if cancel != True and cancel != False:
            self.cancel = [cancel.get_filter()] if isinstance(cancel, EventBinder) else [c.get_filter() for c in cancel]
        else:
            self.cancel = cancel

        if reset != True and reset != False:
            self.reset = [reset.get_filter()] if isinstance(reset, EventBinder) else [r.get_filter() for r in reset]
        else:
            self.reset = reset

        if consume is None:
            self.consume = self.filt
        elif consume != True and consume != False:
            self.consume = [consume.get_filter()] if isinstance(consume, EventBinder) else [c.get_filter() for c in consume]
        else:
            self.consume = consume

        self.period = period
        self.job = None

    def schedule(self, func, event):
        runtime = (datetime.datetime.now() + datetime.timedelta(seconds=self.period)).time()
        loop = asyncio.get_event_loop()
        self.job = loop.call_later(self.period, func, event)

    def cancel_job(self):
        if self.job:
            self.job.cancel()
            self.job = None

    def reschedule(self, func, event):
        self.cancel_job()
        self.schedule(func, event)

    def wrap(self, func):
        def wrapper(event, *args, **kwargs):
            # check if we should consume it
            consume = False
            if self.consume is True:
                consume = self.consume
            elif self.consume:
                for c in self.consume:
                    if c.check(event):
                        consume = True
                        break

            # Check whether event should be delayed
            for f in self.filt:
                if f.check(event):
                    # yes it should be delayed
                    if self.job:
                        # it was already scheduled
                        if self.reset is True:
                            # we always reset
                            self.reschedule(func, event)
                    else:
                        # it hasn't been scheduled yet
                        self.schedule(func, event)
                    if not consume:
                        return func(event, *args, **kwargs)
                    else:
                        return

            if self.job:
                # it's already scheduled so check if we should cancel
                if self.cancel is True:
                    # we always cancel
                    self.cancel_job()
                    if not consume:
                        return func(event, *args, **kwargs)

                elif self.cancel:
                    for c in self.cancel:
                        if c.check(event):
                            self.cancel_job()
                            if not consume:
                                return func(event, *args, **kwargs)

                if self.reset is True:
                    self.reschedule(func, event)
                    if not consume:
                        return func(event, *args, **kwargs)

                elif self.reset:
                    for r in self.reset:
                        if r.check(event):
                            self.reschedule(func, event)
                            if not consume:
                                return func(event, *args, **kwargs)

            # Don't forget to pass it through if we're not capturing it!
            if not consume:
                return func(event, *args, **kwargs)
        return wrapper

class DeDup(EventAugmentation):
    def __init__(self, binder=None, period=5, count=1, method="rolling"):
        """Combine multiple instances of the same event within a certain time
        period. NYI

        """
        LOG.warn("EventAugmentation DeDup: NOT YET IMPLEMENTED")

    def bind(self, func, *args, **kwargs):
        pass

    def wrap(self, func):
        return func
