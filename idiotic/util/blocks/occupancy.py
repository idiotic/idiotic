import asyncio

from idiotic import block
import collections
import time


Event = collections.namedtuple("Event", ("source", "state", "time"))

CLOSED = True
OPEN = False

NULL_EVENT = Event(None, None, 0)


class Occupancy(block.Block):
    def __init__(self, *args, threshold=.45, decay=.93, motion=None, doors=None, sound=None, **kwargs):
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
            diff = self.weights[evt.source] * self.decay ** (time.time() - evt.time)
            prob += diff

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