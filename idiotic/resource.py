from typing import Optional, Iterable
from idiotic import config
import aiohttp
import asyncio


class MissingResource(Exception):
    pass


class Resource:

    initialized = False

    def __init__(self):
        self.available = False
        self.static = False
        self.initialized = False

    async def try_check(self):
        if not self.available:
            raise MissingResource(self)

    def available_hosts(self, config: config.Config) -> Optional[Iterable[str]]:
        """Return a list of hosts where this resource is statically guaranteed to be available.
        This is used during the pre-allocation phase of blocks to determine which nodes the scheduler
        should not attempt to schedule a block on.
        If this resource cannot be statically determined, it should return None or a list of all hosts."""

        return None

    async def run(self):
        self.initialized = True
        await asyncio.sleep(3600)


class HostResource(Resource):
    def __init__(self, node):
        self.node = node
        self.available = config.config.nodename == self.node
        self.initialized = True

    def available_hosts(self, config: config.Config):
        return [self.node]


class HTTPResource(Resource):
    def __init__(self, address):
        self.address = address
        super().__init__()

    async def run(self):
        while True:
            try:
                async with aiohttp.ClientSession() as client:
                    async with client.head(self.address) as response:
                        if response.status == 200 or 300 <= response.status <= 399:
                            self.available = True
                        else:
                            self.available = False
                        self.initialized = True
                    await asyncio.sleep(10)
            except OSError:
                self.available = False
                await asyncio.sleep(20)
