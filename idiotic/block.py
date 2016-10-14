import uuid
from typing import Iterable, Callable, Any, Dict, Set
from idiotic import resource
from idiotic import config as global_config
import idiotic
import asyncio


if False:
    from idiotic.cluster import Cluster


class Block:
    REGISTRY = {}

    running = False

    name = None
    inputs = {}
    resources = []
    config = {}

    def __init__(self, name, inputs=None, resources=None, **config):
        #: A globally unique identifier for the block
        self.name = name

        self.inputs = inputs or {}

        #: List of resources that this block needs
        self.resources = resources or []

        #: The config for this block
        self.config = config or {}

    async def run(self, *args, **kwargs):
        while True:
            await asyncio.sleep(3600)

    async def run_while_ok(self, cluster: 'Cluster'):
        if self.running:
            return

        self.running = True
        while idiotic.node.own_block(self.name) and await self.check_resources():
            await self.run()
        self.running = False
        idiotic.node.cluster.unassign_block(self.name)
        idiotic.node.cluster.assign_block(self)

    def require(self, *resources: resource.Resource):
        self.resources.extend(resources)

    def precheck_nodes(self, config: global_config.Config) -> Set[str]:
        all_nodes = set(config.nodes.keys())

        for req in self.resources:
            nodes = req.available_hosts(config)
            if nodes is not None:
                all_nodes.intersection_update(set(nodes))

        return all_nodes

    async def run_resources(self):
        await asyncio.gather(*[r.run() for r in self.resources])

    async def check_resources(self) -> bool:
        return all((r.available for r in self.resources))

    async def try_resources(self):
        for r in self.resources:
            r.try_check()

    async def output(self, data, *args):
        if not args:
          args = [self.name,]
        for source in args:
            idiotic.node.dispatch({"data": data, "source": self.name+"."+source})


def create(name, block_config):
    block_type = block_config.get("type", "Block")

    inputs = block_config.get("inputs", {})

    for attr in ("type", "inputs"):
        if attr in block_config:
            del block_config[attr]

    block_cls = Block.REGISTRY[block_type]

    res = block_cls(name=name, **block_config)
    res.inputs = inputs

    return res
