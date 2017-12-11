from astral import Astral, Location

from idiotic.config import config as global_config
from idiotic import block
from datetime import date, datetime, timedelta
import logging
import asyncio
import pytz

log = logging.getLogger(__name__)

def construct_location(info):
    if "city" in info:
        a = Astral()
        a.solar_depression = "civil"
        return a[info["city"]]

    loc = Location()

    if "name" in info:
        loc.name = info["name"]

    if "latitude" in info and "longitude" in info:
        loc.latitude = info["latitude"]
        loc.longitude = info["longitude"]

    if "elevation" in info:
        loc.elevation = info["elevation"]

    if "timezone" in info:
        loc.timezone = info["timezone"]

    return loc


class Sun(block.Block):
    def __init__(self, name, **params):
        super().__init__(name, **params)

        default_location = global_config.get("modules", {}).get("suntime", {}).get("location")

        if "location" in params:
            self.location = construct_location(params["location"])
        else:
            self.location = construct_location(default_location)

        self._next_calculate = datetime.now()

    async def _recalculate(self):
        sun = self.location.sun(date.today(), local=True)
        dawn, sunrise, noon, sunset, dusk = sun['dawn'], sun['sunrise'], sun['noon'], sun['sunset'], sun['dusk']

        now = self._localtime()

        state = None
        sun_up = False
        next_event = None

        if dawn < now < sunrise:
            state = 'dawn'
            sun_up = True
            next_event = sunrise
        elif sunrise < now < noon:
            state = 'morning'
            sun_up = True
            next_event = noon
        elif noon < now < sunset:
            state = 'afternoon'
            sun_up = True
            next_event = sunset
        elif sunset < now < dusk:
            state = 'dusk'
            sun_up = False
            next_event = dusk
        elif dusk < now or now < dawn:
            state = 'night'
            sun_up = False

            tomorrow_sun = self.location.sun(date.today() + timedelta(days=1), local=True)
            next_event = tomorrow_sun['dawn']

        self._next_calculate = next_event

        log.debug("Next calculate at" + str(self._next_calculate))

        await self.output(sun_up)
        await self.output(state, 'period_of_day')
        await self.output(sun_up, 'up')
        await self.output(not sun_up, 'down')

    def _localtime(self):
        return pytz.timezone(self.location.timezone).localize(datetime.now())

    async def run(self):
        await self._recalculate()
        while True:
            if self._next_calculate:
                await asyncio.sleep((self._next_calculate - self._localtime()).seconds)

            await self._recalculate()
