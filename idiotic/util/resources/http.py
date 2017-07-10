from idiotic.resource import Resource

import aiohttp
import asyncio
import logging
import time

log = logging.getLogger(__name__)


class HostReachable(Resource):
    def __init__(self, host, port=80):
        super().__init__()
        self.host = host
        self.port = port

    def describe(self):
        return 'http.HostReachable/' + self.host + ':' + str(self.port)

    async def fitness(self):
        return True

        try:
            log.debug("Checking host...")
            start = time.time()
            reader, writer = await asyncio.open_connection(self.host, self.port)
            log.debug("Connection opened!")
            writer.close()
            log.debug("Writer closed")
            return -(time.time() - start) or -1e-6
        except:
            log.exception("Connection chck failed for %s:%d", self.host, self.port)
            return False


class URLReachable(Resource):
    def __init__(self, address):
        super().__init__()
        self.address = address

    def describe(self):
        return 'http.URLReachable/' + self.address

    async def fitness(self):
        async with aiohttp.ClientSession() as client:
            start = time.time()
            async with client.head(self.address) as response:
                if response.status == 200 or 300 <= response.status <= 399:
                    # If we somehow get 0 elapsed time here, just use one microsecond
                    return -(time.time() - start) or -1e-6
        return False

