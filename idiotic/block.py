import uuid
from typing import Iterable, Callable, Any, Dict, Set
from idiotic import resource
from idiotic import config
from idiotic import node


class Input:
    def __init__(self, callback=None):
        self.callback = callback  # type: Callable[[Any], Any]

    def connect(self, receiver):
        """Registers the callback for this input"""
        self.callback = receiver

    def output(self, value):
        if self.callback:
            self.callback(value)


class EventInput(Input):
    def __init__(self, **filters):
        super().__init__()


class Block:
    REGISTRY = {}

    def __init__(self, name, config=None):
        #: A globally unique identifier for the block
        self.name = name

        #: The config for this block
        self.config = config or {}

        #: Map of input receiver names to inputs
        self.inputs = {}  # type: Dict[str, Input]

        #: List of resources that this block needs
        self.resources = []

        self.connect(**self.inputs)

    async def run(self, *args, **kwargs):
        pass

    async def connect(self, **inputs: Dict[str, Input]):
        for name, inputter in inputs.items():
            if hasattr(self, name) and callable(getattr(self, name)):
                inputter.connect(getattr(self, name))
            else:
                raise ValueError("{} has no method named '{}'".format(self, name))

    def require(self, *resources: resource.Resource):
        self.resources.extend(resources)

    async def precheck_nodes(self, config: config.Config) -> Set[str]:
        all_nodes = set(config.nodes.keys())

        for req in self.resources:
            nodes = await req.available_hosts(config)
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
            node.dispatch({"data": data, "source": self.name+"."+source})

def create(name, config):
    block_type = config.get("type", "Block")
    block_cls = Block.REGISTRY[block_type]
    block = block_cls(name=name, config=config)
    node.cluster.assign_block(block)
