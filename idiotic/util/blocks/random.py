import asyncio
import random
from idiotic import block
from idiotic import resource
from idiotic import node


class RandomFloatBlock(block.Block):
    def __init__(self, name, config):
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

class RandomBoolBlock(block.Block):
    def __init__(self, name, config):
        self.name = name
        self.config = {"period": 1
                      }
        self.config.update(config)
        self.resources = []

    async def run(self):
        await asyncio.sleep(self.config['period'])
        val = bool(random.getrandbits(1))
        await self.output(val)

class RandomIntBlock(block.Block):
    def __init__(self, name, config):
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
