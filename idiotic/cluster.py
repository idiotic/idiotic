import asyncio
import functools
import json
import logging
import random

import aiohttp
from aiohttp import web
from pysyncobj import SyncObj, replicated

from idiotic import block
from idiotic import config
from idiotic import util

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
        return self.__data.pop(key)

    def delete(self, key):
        self.pop(key)

    def get(self, key, default=None):
        return self.__data.get(key, default)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __getitem__(self, key):
        return self.get(key)

    def __delitem__(self, key):
        self.delete(key)

    def __str__(self):
        return str(self.__data)


class Cluster:
    def __init__(self, configuration: config.Config):
        if len(configuration.nodes) == 1:
            self.shared_data = {}
            self.single_node = True
        else:
            self.single_node = False
            self.shared_data = util.NestDict(KVStorage(
                '{}:{}'.format(configuration.cluster_host, configuration.cluster_port),
                ['{}:{}'.format(h, p) for h, p in configuration.connect_hosts()],
            ))
        logging.info("Listening for cluster on {}:{}".format(configuration.cluster_host, configuration.cluster_port))
        logging.debug("Connecting to {}".format(list(configuration.connect_hosts())))

        self.shared_data["block_owners"] = {}

        self.config = configuration

    async def find_destinations(self, event):
        return self.config.nodes.keys()

    @property
    def block_owners(self):
        return self.shared_data["block_owners"]

    def block_owner(self, name):
        return self.block_owners.get(name, None)

    def set_block_owner(self, name, owner):
        self.block_owners[name] = owner

    def _assign_block(self, name, nodes):
        if not self.ready():
            return

        # FIXME there is a race condition here
        if self.block_owner(name):
            logging.debug("Block {} is already assigned to {}".format(name, self.block_owner(name)))
            return

        shuffled = list(nodes)
        random.shuffle(shuffled)

        for node in shuffled:
            self.set_block_owner(name, node)
            logging.info("Assigned {} to {}".format(name, node))
            break
        else:
            raise UnassignableBlock(name)

    def ready(self):
        return self.single_node or self.shared_data._isReady()

    def unassign_block(self, name):
        self.set_block_owner(name, None)

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
        return self.cluster.block_owner(name) == self.name

    async def initialize_blocks(self):
        try:
            for name, settings in self.config.blocks.items():
                blk = block.create(name, settings)
                self.blocks[name] = blk

            for name, blk in self.blocks.items():
                # Check that all input blocks exist
                for input_key, input_name in blk.inputs.items():
                    if input_name in self.blocks:
                        continue

                    if '.' in input_name:
                        blkpart, outpart = input_name.rsplit('.', 2)
                        if blkpart in self.blocks:
                            continue

                    raise ValueError("Block {} not found for input to block {}.{}".format(input_name, name, input_key))

                # Set inputs for 'input_to' parameters
                for output_path in blk.input_to:
                    blkname, input_name = output_path.rsplit('.', 2)

                    if blkname not in self.blocks:
                        raise ValueError("Block {} with input {} not found for output from block {}".format(blkname, input_name, name))

                    if input_name in self.blocks[blkname].inputs and self.blocks[blkname].inputs[input_name] is not None:
                        raise ValueError("Block {} already has an input for {}".format(blkname, input_name))

                    # Actually set up the input on the other block
                    self.blocks[blkname].inputs[input_name] = name

                self.cluster.assign_block(blk)
        except:
            log.exception("While initializing blocks...")

    def dispatch(self, event):
        self.events_out.put_nowait(event)

    async def event_received(self, event):
        dests = []
        destnames = []
        for block in self.blocks.values():
            if not self.own_block(block.name):
                continue

            if not block.inputs:
                continue

            for target, output in block.inputs.items():
                if event['source'] == output or event['source'] == "{0}.{0}".format(output):
                    if target is None:
                        dests.append(block)
                        destnames.append(block.name)
                    else:
                        dests.append(getattr(block, target))
                        destnames.append("{}.{}".format(block.name, target))

        log.debug(" * {}({})".format(event['source'], event['data']))
        for dest in destnames:
            log.debug(" |--> {}".format(dest))

        for dest in dests:
            await dest(event['data'])

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
                if self.cluster.block_owner(name) is None:
                    try:
                        self.cluster.assign_block(blk)
                    except UnassignableBlock as e:
                        if blk.optional:
                            logging.warning("Block left unassigned: %s", name)
                        else:
                            raise

                if self.own_block(name) and not blk.running:
                    tasks.append(blk.run_resources)
                    tasks.append(functools.partial(blk.run_while_ok, self.cluster))

            await asyncio.gather(*(asyncio.ensure_future(task()) for task in tasks))

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

    async def rpc_endpoint(self, request: aiohttp.web.Request):
        self.events_in.put_nowait(await request.json())
        return web.Response(text='{"Success": true}', content_type='application/json')

    async def cluster_status(self, request: aiohttp.web.Request):
        res = """
        <!DOCTYPE html public>
        <html>
        <head><title>Cluster Status</title></head>
        <body>
        <table>
        <thead><tr><th>Block</th><th>Owner</th><th>Resources</th></tr></thead>
        <tbody>"""

        for blk, owner in sorted(self.cluster.block_owners.items()):
            res += "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(blk, owner, len(self.blocks[blk].resources))
        res += "</tbody></table></body></html>"

        return web.Response(text=res, content_type='text/html')

    async def run_rpc(self):
        app = web.Application()
        app.router.add_route('POST', '/rpc', self.rpc_endpoint, name='rpc')
        app.router.add_route('GET', '/status', self.cluster_status, name='status')
        handler = app.make_handler()
        await asyncio.get_event_loop().create_server(handler, self.config.cluster['listen'], self.config.cluster['rpc_port'])
