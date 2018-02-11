import asyncio

from idiotic import block
import collections
import time


Event = collections.namedtuple("Event", ("source", "state", "time"))

CLOSED = True
OPEN = False

NULL_EVENT = Event(None, None, 0)

EPSILON = 1e-3


class StagedMotion(block.Block):
    # The first value is the "cooldown" period -- for this many seconds after the initial motion
    #     event, additional motion events will not trigger a stage upgrade
    # The second value is the activation period -- after the cooldown period ends, any motion event
    #     for this many seconds will trigger the next stage.
    # Once the last stage has been reached, if a motion event occurs after the
    DEFAULT_STAGES = [
        (5, 20),
        (30, 60),
        (300, 1800),
    ]

    def __init__(self, *args, stages=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not stages:
            stages = self.DEFAULT_STAGES

        self.stages = stages
        self.cur_stage = None
        self.last_trigger = None

    def __getattr__(self, key):
        if key.startswith("motion_"):
            async def __motion(val):
                # We only care about when motion starts
                if not val:
                    return

                now = time.time()

                if self.cur_stage is None:
                    # First time!
                    self.cur_stage = 0
                    self.last_trigger = now

                    await self.output(True)
                else:
                    if now - self.last_trigger > self.stages[self.cur_stage][0]:
                        # Not in the cooldown state anymore
                        self.last_trigger = now

                        # Move to the next stage if we can
                        if self.cur_stage < len(self.stages) - 1:
                            self.cur_stage += 1

            return __motion
        else:
            raise ValueError("Parameter not declared")

    async def _recalculate(self):
        if self.cur_stage is not None:
            stage_info = self.stages[self.cur_stage]
            if self.last_trigger + stage_info[0] + stage_info[1] <= time.time():
                # The timeout has expired
                self.cur_stage = None
                await self.output(False)

    def get_recalc_time(self):
        if self.cur_stage is not None:
            stage_info = self.stages[self.cur_stage]
            return self.last_trigger + stage_info[0] + stage_info[1]
        else:
            # The earliest we would need to recalculate is if we immediately get a motion event,
            # and then no more and it expires.
            return time.time() + sum(self.stages[0])

    async def run(self):
        while True:
            await asyncio.sleep(self.get_recalc_time() - time.time())
            await self._recalculate()


class Occupancy(block.Block):
    def __init__(self, *args, threshold=.45, decay=.85, motion=None, doors=None, sound=None, **kwargs):
        # Have some sort of thing that, going a certain distance back, calculates each thing's contribution based on a
        # configurable decay rate for each input / input type
        super().__init__(*args, **kwargs)
        self.motion_events = []
        self.door_events = []
        self.sound_events = []

        self.threshold = threshold
        self.decay = decay

        self.weights = collections.defaultdict(lambda: 1.0)

    def latest_events(self):
        motions = reversed(self.motion_events)
        doors = reversed(self.door_events)
        sounds = reversed(self.sound_events)

        motion, door, sound = next(motions, NULL_EVENT), next(doors, NULL_EVENT), next(sounds, NULL_EVENT)

        while motion != NULL_EVENT or door != NULL_EVENT or sound != NULL_EVENT:
            latest = max(motion.time, door.time, sound.time)
            if motion.time == latest:
                yield motion
                motion = next(motions, NULL_EVENT)
            elif door.time == latest:
                yield door
                door = next(door, NULL_EVENT)
            elif sound.time == latest:
                yield sound
                sound = next(sound, NULL_EVENT)

    def probability(self):
        prob = 0.0
        for evt in self.latest_events():
            if not evt.state:
                continue

            diff = self.weights[evt.source] * self.decay ** (time.time() - evt.time)
            prob += diff

            if prob > 1.0:
                prob = 1
                break

            if diff < .01:
                # Nothing will change significantly to
                break

        print("Probability =", prob)

        return prob

    def value(self):
        return self.probability() >= self.threshold

    def get_recalc_time(self):
        return time.time() + 1

    async def _recalculate(self):
        await self.output(self.value())
        await self.output(self.value(), "occupied")
        await self.output(self.probability(), "probability")

    def __getattr__(self, key):
        if key.startswith("motion_"):
            async def __motion(val):
                self.motion_events.append(Event(key[len("motion_"):], val, time.time()))
                await self._recalculate()

            return __motion
        elif key.startswith("door_"):
            async def __door(val):
                self.door_events.append(Event(key[len("door_"):], val, time.time()))
                await self._recalculate()

            return __door
        elif key.startswith("sound_"):
            async def __sound(val):
                self.sound_events.append(Event(key[len("sound_"):], val, time.time()))
                await self._recalculate()

            return __sound
        else:
            raise ValueError("Parameter name not declared")