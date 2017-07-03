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

log = logging.getLogger(__name__)


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
        log.info("Listening for cluster on %s:%s", configuration.cluster_host, configuration.cluster_port)
        log.debug("Connecting to %s", list(configuration.connect_hosts()))

        self.shared_data["block_owners"] = {}
        self.shared_data["resources"] = {}

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

    def _assign_block(self, name, fitnesses):
        if not self.ready():
            return

        # FIXME there is a race condition here
        if self.block_owner(name):
            log.debug("Block %s is already assigned to %S", name, self.block_owner(name))
            return

        eligible = sorted([(fit, node) for node, fit in fitnesses.items() if fit is not False])

        if len(eligible):
            node = eligible[-1][1]
            self.set_block_owner(name, node)
            log.info("Assigned %s to %s", name, node)
        else:
            raise UnassignableBlock(name)

    @property
    def resources(self):
        return self.shared_data["resources"]

    def set_resource_fitness(self, resource, fitness):
        desc = resource.describe()

        if desc not in self.resources:
            self.resources[desc] = {}

        self.resources[desc][self.config.nodename] = fitness

    def resource_checked_here(self, resource):
        return self.config.nodename in self.resources.get(resource.describe(), {})

    def resource_checked_all(self, resource):
        return len(self.resources.get(resource.describe(), {})) == len(self.config.nodes)

    def resource_fitnesses(self, resource):
        return dict(self.resources.get(resource.describe(), {}))

    def resource_targets(self, resource):
        return {k: v for k, v in self.resource_fitnesses(resource).items() if v}

    def block_resource_fitnesses(self, block: block.Block):
        """Returns a map of nodename to average fitness value for this block.
        Assumes that required resources have been checked on all nodes."""

        # Short-circuit! My algorithm is terrible, so it doesn't work well for the edge case where
        # the block has no requirements
        if not block.resources:
            return {n: 1 for n in self.config.nodes.keys()}

        node_fitnesses = {}

        for resource in block.resources:
            resource_fitnesses = self.resource_fitnesses(resource)

            max_fit = max(resource_fitnesses.values())
            min_fit = min(resource_fitnesses.values())

            for node, fitness in resource_fitnesses.items():
                if node not in node_fitnesses:
                    node_fitnesses[node] = {}

                if not fitness:
                    # Since we're rescaling, 0 is now an OK value...
                    # We will check for `is False` after this
                    node_fitnesses[node][resource.describe()] = False
                else:
                    if max_fit - min_fit:
                        node_fitnesses[node][resource.describe()] = (fitness - min_fit) / (max_fit - min_fit)
                    else:
                        # All the values are the same, default to 1
                        node_fitnesses[node][resource.describe()] = 1.0

        res = {}

        for node, res_fits in node_fitnesses.items():
            fit_sum = 0
            for res_desc, fit in res_fits.items():
                if fit is False:
                    fit_sum = False
                    break

                fit_sum += fit

            if fit_sum is False:
                # Skip this node entirely
                res[node] = False
                continue

            res[node] = fit_sum

        return res

    def ready(self):
        return self.single_node or self.shared_data._isReady()

    def unassign_block(self, name):
        self.set_block_owner(name, None)

    def reassign_block(self, block: block.Block):
        self.unassign_block(block.name)
        self.assign_block(block)

    def assign_block(self, block: block.Block):
        log.debug("Assigning block %s", block.name)
        self._assign_block(block.name, self.block_resource_fitnesses(block))


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
        log.debug("Initializing blocks...")
        try:
            for name, settings in self.config.blocks.items():
                blk = block.create(name, settings)
                self.blocks[name] = blk

            blk_inits = []

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

                log.debug("Block %s mostly initialized", name)

                async def wait_for_resource(node, res):
                    log.debug("Waiting for resource %s...", res.describe())

                    if not node.cluster.resource_checked_here(res):
                        log.debug("Checking resource %s", res.describe())
                        try:
                            fitness = await res.fitness()
                        except:
                            log.exception("Checking resource %s failed with exception", res.describe())
                            fitness = 0
                        node.cluster.set_resource_fitness(res, fitness)

                        log.debug("Resource %s checked with fitness=%s", res.describe(), fitness)

                    while not node.cluster.resource_checked_all(res):
                        log.debug("Waiting for resource " + res.describe())
                        await asyncio.sleep(5)

                async def blk_init(node, blk_):
                    res_inits = []
                    for resource in blk_.resources:
                        res_inits.append(wait_for_resource(node, resource))

                    await asyncio.gather(*res_inits)
                    node.cluster.assign_block(blk_)

                blk_inits.append(blk_init(self, blk))
            await asyncio.gather(*blk_inits)
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

        log.debug(" * %s(%s)", event['source'], event['data'])
        for dest in destnames:
            log.debug(" |--> %s", dest)

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
        blacklist = set()
        while True:
            tasks = []
            for name, blk in self.blocks.items():
                if self.cluster.block_owner(name) is None and name not in blacklist:
                    try:
                        self.cluster.assign_block(blk)
                    except UnassignableBlock as e:
                        blacklist.add(name)
                        if blk.optional:
                            log.warning("Block left unassigned: %s", name)
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
                log.exception("While running messaging")

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
