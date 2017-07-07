import asyncio
import random
from idiotic import block
from idiotic import resource
from idiotic import node


class Float(block.Block):
    def __init__(self, name, **config):
        self.name = name
        self.config = {"period": 1,
                       "min": 0,
                       "max": 1
                      }
        self.config.update(config)

        self.inputs = {}
        self.resources = []

    async def run(self):
        await asyncio.sleep(self.config['period'])
        val = random.random()*(self.config['max']-self.config['min'])+self.config['min']
        await self.output(val)


class Bool(block.Block):
    def __init__(self, name, **config):
        self.name = name
        self.config = {"period": 1
                      }
        self.config.update(config)
        self.resources = []

    async def run(self):
        await asyncio.sleep(self.config['period'])
        val = bool(random.getrandbits(1))
        await self.output(val)


class Int(block.Block):
    def __init__(self, name, **config):
        self.name = name
        self.config = {"period": 1,
                       "min": 0,
                       "max": 1
                      }
        self.config.update(config)
        self.resources = []

    async def run(self):
        await asyncio.sleep(self.config['period'])
        val = random.randrange(self.config['min'], self.config['max'])
        await self.output(val)


class List(block.Block):
    def __init__(self, name, period=1, items=None):
        super().__init__(name)
        self.period = period
        self.items = items or []

    async def run(self):
        await asyncio.sleep(self.period)
        await self.output(random.choice(self.items))
