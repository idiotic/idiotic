import asyncio
import random
from idiotic import block
from idiotic import resource
from idiotic import node


class Float(block.Block):
    def __init__(self, name, period=1, min=0, max=1, **config):
        super().__init__(name, **config)

        self.period = period
        self.min = min
        self.max = max

    async def run(self):
        await asyncio.sleep(self.period)
        val = random.random()*(self.max-self.min)+self.min
        await self.output(val)


class Bool(block.Block):
    def __init__(self, name, period=1, **config):
        super().__init__(name, **config)

        self.period = period

    async def run(self):
        await asyncio.sleep(self.period)
        val = bool(random.getrandbits(1))
        await self.output(val)


class Int(block.Block):
    def __init__(self, name, period=1, min=0, max=1, **config):
        super().__init__(name, **config)

        self.period = period
        self.min = min
        self.max = max

    async def run(self):
        await asyncio.sleep(self.period)
        val = random.randrange(self.min, self.max)
        await self.output(val)


class List(block.Block):
    def __init__(self, name, period=1, items=None, **config):
        super().__init__(name, **config)
        self.period = period
        self.items = items or []

    async def run(self):
        await asyncio.sleep(self.period)
        await self.output(random.choice(self.items))
