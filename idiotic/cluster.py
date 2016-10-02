from idiotic import config
from idiotic import block
import idiotic
import pysyncobj
import logging
import asyncio
import aiohttp
from aiohttp import web
from threading import RLock
import functools
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
        self.block_owners = {}
        self.block_lock = RLock()
        self.resources = {}
        self.jobs = []

    async def find_destinations(self, event):
        return self.config.nodes.keys()

    def get_rpc_url(self, node):
        return "http://{}:{}/rpc".format(node, self.config.cluster["rpc_port"])

    @pysyncobj.replicated
    def _assign_block(self, name, nodes):
        with self.block_lock:
            if not self._isLeader():
                print("I am not the leader!")
                return

            if self.block_owners.get(name, None):
                print("Block {} is already assigned to {}".format(name, self.block_owners.get(name)))
                return

            for node in nodes:
                self.block_owners[name] = node
                break
            else:
                raise UnassignableBlock(name)

    @pysyncobj.replicated
    def unassign_block(self, name):
        with self.block_lock:
            self.block_owners[name] = None

    def reassign_block(self, name):
        self.unassign_block(name)
        self.assign_block(name)

    def assign_block(self, block: block.Block):
        print("Assigning block", block.name)
        self._assign_block(block.name, block.precheck_nodes(self.config))
        print("Assigned block", block.name)


class Node:
    def __init__(self, name: str, cluster: Cluster, config: config.Config):
        self.name = name
        self.cluster = cluster
        self.config = config

        self.blocks = {}

        self.events_out = asyncio.Queue()
        self.events_in = asyncio.Queue()

        self._was_ready = False

    def own_block(self, name):
        return self.cluster.block_owners.get(name, None) == self.name

    async def initialize_blocks(self):
        for name, settings in self.config.blocks.items():
            blk = block.create(name, settings)
            self.cluster.assign_block(blk)
            self.blocks[name] = blk

    def dispatch(self, event):
        self.events_out.put_nowait(event)

    async def event_received(self, event):
        print("Event received!", event)
        dests = []
        for block in self.blocks.values():
            if not self.own_block(block.name):
                print("{} owns block {}".format(self.cluster.block_owners[block.name], block.name))
                continue
            print("We own block {}".format(block.name))

            if 'inputs' not in block.config:
                print("{} has no inputs".format(block.name))
                continue
            print("Block {} has inputs".format(block.name))

            for target, blockid in block.config['inputs'].items():
                if event['source'].startswith(blockid):
                    print("Event goes to ", block.name)
                    dests.append(getattr(block, target))
                else:
                    print("Source {} does not match {}".format(event['source'], blockid))

        for dest in dests:
            await dest(event['data'])
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
            tasks = []
            for name, blk in self.blocks.items():
                if self.own_block(name) and not blk.running:
                    print("We own {}, starting!".format(name))
                    tasks.append(blk.run_resources)
                    tasks.append(functools.partial(blk.run_while_ok, self.cluster))
            await asyncio.gather(*[task() for task in tasks])

    async def run_messaging(self):
        while True:
            event = await self.events_in.get()
            await self.event_received(event)

    async def run_dispatch(self):
        while True:
            event = await self.events_out.get()

            for dest in await self.cluster.find_destinations(event):
                url = self.cluster.get_rpc_url(dest)
                # Screw you aiohttp, I do what I want!
                try:
                    async with aiohttp.ClientSession() as client:
                        async with client.post(url, data=json.dumps(event), headers={'Content-Type': 'application/json'}) as request:
                            log.debug(await request.json())
                except:
                    print("An error happened :(")

    async def rpc_endpoint(self, request: aiohttp.Request):
        log.debug("WOW")
        self.events_in.put_nowait(await request.json())
        return web.Response(text='{"Success": true}', content_type='application/json')

    async def run_rpc(self):
        app = web.Application()
        app.router.add_route('POST', '/rpc', self.rpc_endpoint, name='rpc')
        handler = app.make_handler()
        await asyncio.get_event_loop().create_server(handler, self.config.cluster['listen'], self.config.cluster['rpc_port'])
