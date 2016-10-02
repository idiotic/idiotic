import requests
from idiotic import block
from idiotic import resource

class TeapotBlock(block.Block):
    def __init__(self, config={}, global_config={}):
        self.config = {"address": "https://api.particle.io",
                       "path": "/v1/devices/",
                       "access_token": "",
                       "device_id": ""
                      }
        self.config.update(config)

        self.inputs = {"temperature": block.Input(),
                       "hold": block.Input()
                      }
        self.resources = [resource.PingResource(self.config['address'])]
        self.connect(**self.inputs)
        self.hold_start = 0
        self.hold_duration = 0

    def temperature(self, value):
        requests.get("{}{}{}/set_temp".format(self.config['address'], self.config['path'], self.config['device_id']), data={'access_token': self.config['access_token'], 'args': str(value)})

    def hold(self, value):
        self.hold_start = time.time()
        self.hold_duration = value

    async def run(self):
        while True:
            await asyncio.sleep(20)
            if (time.time() - self.hold_duration) < self.hold_start:
                requests.get("{}{}{}/set_hold".format(self.config['address'], self.config['path'], self.config['device_id']), data={'access_token': self.config['access_token'], 'args': str(30)})
