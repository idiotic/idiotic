import requests
from idiotic import block
from idiotic import resource
from idiotic import node
import asyncio
import aiohttp
import wink

class WinkDeviceNotFound(Exception):
    pass

class WinkBlock(block.Block):
    def __init__(self, name, config):
        self.name = name
        self.config = {"base_url": "https://winkapi.quirky.com",
                       "client_id": "quirky_wink_android_app",
                       "client_secret": "e749124ad386a5a35c0ab554a4f2c045",
                       "username": "",
                       "password": "",
                       "name": "",
                       "label": "",
                       "id": "",
                      }
        self.config.update(config)

        self.inputs = {}
        self.resources = [resource.HTTPResource(self.config['base_url'])]
        self.auth = wink.auth(username=self.config['username'], password=self.config['password'])
        self.wink = wink.Wink(auth, save_auth=False)
        self.device = None
        def find(self):
            devices = self.wink.device_list()
            for field in ['id', 'label', 'name']:
                for dev in devices:
                    value = dev.data.get(field)
                    if value and value == self.config[field]:
                        return dev
        self.device = find()
        if not self.device:
            raise WinkDeviceNotFound("None of the provided criteria matched any devices in your Wink account")

    async def run(self):
        pass

class WinkDimmer(WinkBlock):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.power_state = None
        self.brightness = None

    def brightness(self, value):
        self.brightness = value
        yield from loop.run_in_executor(None, self.device.set_brightness, value)

    def power(self, value):
        self.power_state = value
        if value:
            yield from loop.run_in_executor(None, self.device.turn_on)
        else:
            yield from loop.run_in_executor(None, self.device.turn_off)

class WinkToggle(WinkBlock):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.power_state = None

    def power(self, value):
        self.power_state = value
        if value:
            yield from loop.run_in_executor(None, self.device.turn_on)
        else:
            yield from loop.run_in_executor(None, self.device.turn_off)
