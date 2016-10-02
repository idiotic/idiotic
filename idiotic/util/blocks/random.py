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
        while await self.check_resources():
            await asyncio.sleep(self.config['period'])
            await self.output((random.random()+self.config['min'])*(self.config['max']-self.config['min']))
        node.cluster.assign_block()
