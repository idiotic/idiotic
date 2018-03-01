import logging

from urllib.parse import urlparse, urlunparse

from idiotic import block
from idiotic.util.resources import http
import aiohttp
import asyncio
import json

import types

log = logging.getLogger(__name__)


class HTTP(block.Block):
    def __init__(self, name, url, method="GET", parameters=None, defaults=None, skip_repeats=False, format_data=True,
                 output=True, data=None, **options):
        super().__init__(name, **options)

        self.url = url
        self.parameters = parameters or []
        self.method = method

        self.data = data or {}
        self.defaults = defaults or {}
        self.skip_repeats = skip_repeats
        self.format_data = format_data

        if output:
            if output is True:
                self.outputter = lambda d: d
            elif output == "int":
                self.outputter = int
            elif output == "float":
                self.outputter = float
            elif output == "bool":
                self.outputter = bool
            elif output == "str":
                self.outputter = str
            elif output == "json":
                self.outputter = json.loads
            else:
                raise ValueError("Invalid output type: {}".format(output))
        else:
            self.outputter = None

        parsed_url = urlparse(url, scheme='http')
        url_root = urlunparse((parsed_url[0], parsed_url[1], '', '', '', ''))

        #: Options
        self.options = options

        self._param_dict = {n: self.defaults.get(n, None) for n in self.parameters}

        for name in self.parameters:
            async def setparam(self, val):
                await self._setparam(name, val)

            setattr(self, name, types.MethodType(setparam, self))

        self.inputs = {}
        self.resources = [http.URLReachable(url_root)]

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
        while True:
            try:
                async with aiohttp.ClientSession() as client:
                    async with client.request(
                            self.method,
                            self.url.format(**self._param_dict),
                            data=self.formatted_data(),
                    ) as request:
                        res = await request.text()

                        if self.outputter:
                            output_val = self.outputter(res)
                            await self.output(output_val)
                        break
            except IOError:
                log.error("%s: Unable to retrieve %s", self.name, self.url)
                await asyncio.sleep(5)
