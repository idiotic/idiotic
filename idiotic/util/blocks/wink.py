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
                       "wink_name": "",
                       "wink_label": "",
                       "wink_id": "",
                      }
        self.config.update(config)

        self.inputs = {}
        self.resources = [resource.HTTPResource(self.config['base_url'])]
        self.auth = wink.auth(**self.config)
        self.wink = wink.Wink(self.auth, save_auth=False)
        self.device = None
        self.device = self.find()
        if not self.device:
            raise WinkDeviceNotFound("None of the provided criteria matched any devices in your Wink account")

    def find(self):
        devices = self.wink.device_list()
        for field in ['id', 'label', 'name']:
            for dev in devices:
                value = dev.data.get(field)
                if value and value == self.config["wink_" + field]:
                    return dev

    async def run(self):
        pass

class WinkDimmer(WinkBlock):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.power_state = None
        self.brightness = None

    async def brightness(self, value):
        self.brightness = value
        await loop.run_in_executor(None, self.device.set_brightness, value)

    async def power(self, value):
        self.power_state = value
        if value:
            await loop.run_in_executor(None, self.device.turn_on)
        else:
            await loop.run_in_executor(None, self.device.turn_off)

class WinkToggle(WinkBlock):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.power_state = None

    async def power(self, value):
        self.power_state = value
        if value:
            await loop.run_in_executor(None, self.device.turn_on)
        else:
            await loop.run_in_executor(None, self.device.turn_off)
