import uuid
from typing import Iterable, Callable, Any, Dict, Set
from idiotic import resource
from idiotic import config
import idiotic


class Block:
    REGISTRY = {}

    def __init__(self, name, config=None):
        #: A globally unique identifier for the block
        self.name = name

        #: The config for this block
        self.config = config or {}

        #: Map of input receiver names to inputs
        self.inputs = {}  # type: Dict[str, Callable]

        #: List of resources that this block needs
        self.resources = []

    async def run(self, *args, **kwargs):
        pass

    def require(self, *resources: resource.Resource):
        self.resources.extend(resources)

    def precheck_nodes(self, config: config.Config) -> Set[str]:
        all_nodes = set(config.nodes.keys())

        for req in self.resources:
            nodes = req.available_hosts(config)
            if nodes is not None:
                all_nodes.intersection_update(set(nodes))

        return all_nodes

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

    block_cls = Block.REGISTRY[block_type]

    return block_cls(name=name, config=block_config)
