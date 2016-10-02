import requests
from idiotic import block
from idiotic import resource

class TeapotBlock(block.Block):
    def __init__(self):
        self.inputs = {"temperature": block.Input(),
                       "hold": block.Input()
                      }
        self.resources = [resource.PingResource(config['address'])]
        self.connect(**self.inputs)

    def temperature(self, value):
        requests.get("{}{}{}/set_temp".format(config('address', 'https://api.particle.io'), config('path', '/v1/devices/'), config('device_id')), data={'access_token': config('access_token'), 'args': str(value)})

    def hold(self, value):
        requests.get("{}{}{}/set_hold".format(config('address', 'https://api.particle.io'), config('path', '/v1/devices/'), config('device_id')), data={'access_token': config('access_token'), 'args': str(value)})
