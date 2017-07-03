from idiotic.resource import Resource

import aiohttp
import time


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

