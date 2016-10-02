from idiotic import config
from idiotic import block
import idiotic
import pysyncobj
import logging
import asyncio
import aiohttp
from aiohttp import web
from threading import RLock
import json

log = logging.Logger('idiotic.cluster')


class UnassignableBlock(Exception):
    pass


class Cluster(pysyncobj.SyncObj):
    def __init__(self, configuration: config.Config):
        super(Cluster, self).__init__(
            '{}:{}'.format(configuration.hostname, configuration.cluster['port']),
            [h for h in configuration.cluster['connect'] if not h.startswith(configuration.hostname + ':')]
        )
        self.config = configuration
        self.blocks = {}
        self.block_owners = {}
        self.block_lock = RLock()
        self.resources = {}
        self.jobs = []

    async def find_destinations(self, event):
        return self.config.nodes.keys()

    def get_rpc_url(self, node):
        return "http://{}:{}/rpc".format(node, self.config.cluster["rpc_port"])

    @pysyncobj.replicated
    def assign_block(self, block: block.Block):
        with self.block_lock:
            self.blocks[block.name] = block

            self.block_owners[block.name] = None
            nodes = block.precheck_nodes(self.config)

            for node in nodes:
                self.block_owners[block.name] = node
                # Later: somehow tell the other node they have a new block
                break
            else:
                raise UnassignableBlock(block)


class Node:
    def __init__(self, name: str, cluster: Cluster, config: config.Config):
        self.name = name
        self.cluster = cluster
        self.config = config

        self.events_out = asyncio.Queue()
        self.events_in = asyncio.Queue()

        self._was_ready = False

    async def initialize_blocks(self):
        for name, settings in self.config.blocks.items():
            self.cluster.assign_block(block.create(name, settings))

    def dispatch(self, event):
        self.events_out.put_nowait(event)

    def event_received(self, event):
        log.debug("Event received: {}", event)
        # don't know what to do here

    async def run(self):
        await asyncio.gather(
            self.run_dispatch(),
            self.run_rpc(),
            self.run_messaging(),
            self.run_blocks(),
        )

    async def run_blocks(self):
        while True:
            if self._was_ready != self.cluster._isReady():
                print("Cluster {} ready!".format("NOT" if self._was_ready else "is"))
                self._was_ready = not self._was_ready

            for name, blk in self.cluster.blocks.items():
                if self.cluster.block_owners[name] == self.name:
                    try:
                        await blk.run()
                    except Exception as e:
                        log.exception(e)
            await asyncio.sleep(.01)

    async def run_messaging(self):
        while True:
            event = await self.events_in.get()
            self.event_received(event)

    async def run_dispatch(self):
        while True:
            event = await self.events_out.get()

            for dest in await self.cluster.find_destinations(event):
                url = self.cluster.get_rpc_url(dest)
                # Screw you aiohttp, I do what I want!
                async with aiohttp.ClientSession() as client:
                    async with client.post(url, data=json.dumps(event), headers={'Content-Type': 'application/json'}) as request:
                        log.debug(await request.json())

    async def rpc_endpoint(self, request: aiohttp.Request):
        log.debug("WOW")
        self.events_in.put_nowait(await request.json())
        return web.Response(text='{"Success": true}', content_type='application/json')

    async def run_rpc(self):
        app = web.Application()
        app.router.add_route('POST', '/rpc', self.rpc_endpoint, name='rpc')
        handler = app.make_handler()
        await asyncio.get_event_loop().create_server(handler, self.config.cluster['listen'], self.config.cluster['rpc_port'])
