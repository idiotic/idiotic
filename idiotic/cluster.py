from pysyncobj import SyncObj, replicated
from idiotic import config
from idiotic import block

import aiohttp
from aiohttp import web

import functools
import logging
import asyncio
import random
import json

log = logging.Logger('idiotic.cluster')


class UnassignableBlock(Exception):
    pass


class KVStorage(SyncObj):
    def __init__(self, selfAddress, partnerAddrs):
        super(KVStorage, self).__init__(selfAddress, partnerAddrs)
        self.__data = {}

    @replicated
    def set(self, key, value):
        self.__data[key] = value

    @replicated
    def pop(self, key):
        self.__data.pop(key, None)

    def get(self, key, default=None):
        return self.__data.get(key, default)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __getitem__(self, key):
        return self.get(key)

    def __str__(self):
        return str(self.__data)


class Cluster:
    def __init__(self, configuration: config.Config):
        if len(configuration.nodes) == 1:
            self.block_owners = {}
            self.single_node = True
        else:
            self.single_node = False
            self.block_owners = KVStorage(
                '{}:{}'.format(configuration.cluster_host, configuration.cluster_port),
                ['{}:{}'.format(h, p) for h, p in configuration.connect_hosts()],
            )
        print("Listening for cluster on {}:{}".format(configuration.cluster_host, configuration.cluster_port))
        print("Connecting to", list(configuration.connect_hosts()))

        self.config = configuration

    async def find_destinations(self, event):
        return self.config.nodes.keys()

    def _assign_block(self, name, nodes):
        if not self.ready():
            return

        if self.block_owners.get(name, None):
            print("Block {} is already assigned to {}".format(name, self.block_owners.get(name)))
            return

        shuffled = list(nodes)
        random.shuffle(shuffled)

        for node in shuffled:
            self.block_owners[name] = node
            print("Assigned {} to {}".format(name, node))
            break
        else:
            raise UnassignableBlock(name)

    def ready(self):
        return self.single_node or self.block_owners._isReady()

    def unassign_block(self, name):
        self.block_owners[name] = None

    def reassign_block(self, name):
        self.unassign_block(name)
        self.assign_block(name)

    def assign_block(self, block: block.Block):
        self._assign_block(block.name, block.precheck_nodes(self.config))


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
                continue

            if not block.inputs:
                continue

            for target, blockid in block.inputs.items():
                if event['source'].startswith(blockid):
                    log.debug("Event goes to ", block.name)
                    dests.append(getattr(block, target))

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
                print("Checking {}".format(name))
                if self.cluster.block_owners[name] is None:
                    self.cluster.assign_block(blk)

                if self.own_block(name) and not blk.running:
                    tasks.append(blk.run_resources)
                    print("About to run {}".format(name))
                    tasks.append(functools.partial(blk.run_while_ok, self.cluster))
            print("There are {} tasks".format(len(tasks)))
            await asyncio.gather(*(task() for task in tasks))

    async def run_messaging(self):
        while True:
            try:
                event = await self.events_in.get()
                await self.event_received(event)
            except:
                logging.exception("While running messaging")

    async def run_dispatch(self):
        while True:
            event = await self.events_out.get()

            for dest in await self.cluster.find_destinations(event):
                if dest == self.name:
                    self.events_in.put_nowait(event)
                else:
                    url = self.config.get_rpc_url(dest)
                    # Screw you aiohttp, I do what I want!
                    try:
                        async with aiohttp.ClientSession() as client:
                            async with client.post(url, data=json.dumps(event), headers={'Content-Type': 'application/json'}) as request:
                                log.debug(await request.json())
                    except:
                        log.exception("Exception occurred in run_dispatch()")

    async def rpc_endpoint(self, request: aiohttp.Request):
        log.debug("WOW")
        self.events_in.put_nowait(await request.json())
        return web.Response(text='{"Success": true}', content_type='application/json')

    async def run_rpc(self):
        app = web.Application()
        app.router.add_route('POST', '/rpc', self.rpc_endpoint, name='rpc')
        handler = app.make_handler()
        await asyncio.get_event_loop().create_server(handler, self.config.cluster['listen'], self.config.cluster['rpc_port'])
