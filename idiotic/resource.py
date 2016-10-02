from typing import Optional, Iterable
from idiotic import config
import pyping

class MissingResource(Exception):
    pass


class Resource:
    def __init__(self):
        self.available = False
        self.static = False

    async def try_check(self):
        if not self.available:
            raise MissingResource(self)

    async def available_hosts(self, config: config.Config) -> Optional[Iterable[str]]:
        """Return a list of hosts where this resource is statically guaranteed to be available.
        This is used during the pre-allocation phase of blocks to determine which nodes the scheduler
        should not attempt to schedule a block on.
        If this resource cannot be statically determined, it should return None or a list of all hosts."""

        return None

    async def run(self):
        pass

class PingResource(Resource):
    def __init__(self, address):
        self.address = address
        super().__init__()

    async def run(self):
        while True:
            await asyncio.sleep(10)
            response = pyping.ping(self.address)
            if response.ret_code == 0:
                self.available = True
            else:
                self.available = False
