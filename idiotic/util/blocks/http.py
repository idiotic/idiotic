import types

import functools
import requests
from idiotic import block
from idiotic import resource
from idiotic import node
from idiotic import config as global_conf
import asyncio
import aiohttp
import wink
import re


class HTTP(block.Block):
    def __init__(self, name, url, method="GET", parameters=None, defaults=None, skip_repeats=False, format_data=True):
        self.name = name

        self.url = url
        self.parameters = parameters or []
        self.method = method

        self.data = {}
        self.defaults = defaults or {}
        self.skip_repeats = skip_repeats
        self.format_data = format_data

        self._param_dict = {n: defaults.get(n, None) for n in self.parameters}

        for name in self.parameters:
            async def setparam(self, val):
                await self._setparam(name, val)

            setattr(self, name, types.MethodType(setparam, self))

        self.inputs = {}
        self.resources = [resource.HTTPResource(self.url)]

    async def _setparam(self, name, value):
        if not self.skip_repeats or value != self._param_dict.get(name):
            self._param_dict[name] = value
            await self.perform()

    def formatted_data(self):
        if self.format_data:
            return {
                k: v.format(**self.data) for k, v in self._param_dict.items()
            }
        else:
            return self.data

    async def perform(self, *_):
        async with aiohttp.ClientSession() as client:
            async with client.request(
                    self.method,
                    self.url.format(**self._param_dict),
                    data=self.formatted_data(),
            ) as request:
                print(await request.text())

    async def run(self):
        pass
