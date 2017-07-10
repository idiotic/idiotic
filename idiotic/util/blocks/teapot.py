from idiotic.util.resources import http
from idiotic import block
import logging
import asyncio
import aiohttp
import time

log = logging.getLogger(__name__)


class Teapot(block.Block):
    def __init__(self, name, **config):
        super().__init__(name, **config)
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
        self.require(http.HostReachable('api.particle.io', 443))
        self.hold_start = 0
        self.hold_duration = 0

    async def temperature(self, value):
        log.debug("setting temp to %s", value)
        async with aiohttp.ClientSession() as client:
            async with client.post(
                    "{}{}{}/set_temp".format(self.config['address'], self.config['path'], self.config['device_id']),
                    data={'access_token': self.config['access_token'], 'args': str(value)}
            ) as request:
                await request.text()

    async def hold(self, value):
        log.debug("holding for %s", value)
        self.hold_start = time.time()
        self.hold_duration = value

    async def run(self):
        if (time.time() - self.hold_duration) < self.hold_start:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                        "{}{}{}/set_hold".format(self.config['address'], self.config['path'], self.config['device_id']),
                        data={'access_token': self.config['access_token'], 'args': str(30)}
                ) as request:
                        await request.text()
        await asyncio.sleep(5)
