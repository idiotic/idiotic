import asyncio
import random
from idiotic import block
from idiotic import resource
from idiotic import node


class RandomBlock(block.Block):
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
        print("Setting random value of {}".format(val))
        await self.output(val)
