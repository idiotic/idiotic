import requests
from idiotic import block
from idiotic import resource
from idiotic import node
import asyncio
import time

class TeapotBlock(block.Block):
    def __init__(self, name, config):
        self.name = name
        self.config = {"address": "https://api.particle.io",
                       "path": "/v1/devices/",
                       "access_token": "",
                       "device_id": ""
                      }
        self.config.update(config)

        self.inputs = {"temperature": self.temperature,
                       "hold": self.hold
                      }
        self.resources = [resource.HTTPResource(self.config['address'])]
        self.hold_start = 0
        self.hold_duration = 0

    def temperature(self, value):
        print("setting temp to {}".format(value))
        requests.get("{}{}{}/set_temp".format(self.config['address'], self.config['path'], self.config['device_id']), data={'access_token': self.config['access_token'], 'args': str(value)})

    def hold(self, value):
        print("holding for {}".format(value))
        self.hold_start = time.time()
        self.hold_duration = value

    async def run(self):
        while await self.check_resources():
            await asyncio.sleep(20)
            if (time.time() - self.hold_duration) < self.hold_start:
                requests.get("{}{}{}/set_hold".format(self.config['address'], self.config['path'], self.config['device_id']), data={'access_token': self.config['access_token'], 'args': str(30)})
        node.cluster.assign_block(self)
