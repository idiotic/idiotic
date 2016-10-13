import requests
from idiotic import block
from idiotic import resource
from idiotic import node
from idiotic import config as global_conf
import asyncio
import aiohttp
import wink
import re

CODE_REGEX = re.compile(r"^([A-Pa-p])([1-9]|1[0-6])$")


class InvalidCodeError(Exception):
    pass


class X10(block.Block):
    def __init__(self, name, config):
        self.name = name
        self.config = {
            "base_url": "http://localhost:5000",
            "code": "",
            "house": "",
            "item": "",
        }

        self.config.update(global_conf.config.get("modules", {}).get("x10", {}))
        self.config.update(config)

        if self.config["code"]:
            self.code = self.config["code"].lower()

            match = CODE_REGEX.match(self.code)
            if not match:
                raise InvalidCodeError("Code must be in {A..P}{1..16} format")

            self.house, self.item = match.groups()

        elif self.config["house"] and self.config["item"]:
            if self.config["house"] not in "ABCDEFGHIJKLMNOPabcdefghijklmnop":
                raise InvalidCodeError("House must be in {A..P}")
            if self.config["item"] not in list(range(1, 17)):
                raise InvalidCodeError('Item must be in {1..16}')
            self.house = self.config["house"].lower()
            self.item = self.config["item"].lower()
            self.code = self.house + self.item

        else:
            raise InvalidCodeError("Code or house and item must be provided")

        self.inputs = {}
        self.resources = [resource.HTTPResource(self.config['base_url'])]

    async def _action(self, action):
        async with aiohttp.ClientSession() as client:
            async with client.get(
                    "{}/{}/{}/{}".format(self.config['base_url'], action, self.house, self.item)
            ) as request:
                print(await request.text())

    async def on(self):
        await self._action('on')

    async def off(self):
        await self._action('off')

    async def power(self, val):
        await (self.on if val else self.off)()

    async def run(self):
        pass

class X10AllLights(X10):
    def __init__(self, name, config):
        super().__init__(name, config)

        self.item = "0"
        self.code = self.house + self.item
