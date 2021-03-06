import asyncio

import functools

from idiotic.block import Block
from idiotic.util.resources import module


class DHT(Block):
    def __init__(self, *args, sensor='DHT22', pin=None, interval=None, **kwargs):
        super().__init__(*args, **kwargs)

        if pin is None:
            raise ValueError("Pin is required")

        self.sensor = sensor
        self.pin = pin
        self.interval = interval
        self._sensor = None
        self._perform = None
        self._lock = asyncio.Lock()

        self.require(module.Module('Adafruit_DHT'))

    async def run(self):
        import Adafruit_DHT

        if self.sensor == 'DHT11':
            sensor = Adafruit_DHT.DHT11
        elif self.sensor == 'DHT22':
            sensor = Adafruit_DHT.DHT22
        elif self.sensor == 'AM2302':
            sensor = Adafruit_DHT.AM2302
        else:
            raise ValueError("Invalid sensor - must be DHT11, DHT22, or AM2302")

        self._perform = functools.partial(Adafruit_DHT.read_retry, sensor, self.pin)

        if self.interval:
            while True:
                await self.update()
                await asyncio.sleep(self.interval)
        else:
            await super().run()

    async def update(self):
        # Don't bother re-running this if it's already running
        if self._lock.locked():
            return

        async with self._lock:
            humidity, temp = await asyncio.get_event_loop().run_in_executor(None, self._perform)
            await self.output((humidity, temp))
            await self.output(temp, "temperature")
            await self.output(humidity, "humidity")


class DHT11(DHT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, sensor='DHT11', **kwargs)


class DHT22(DHT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, sensor='DHT22', **kwargs)


class AM2302(DHT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, sensor='AM2302', **kwargs)
