import logging
from typing import Set
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
    input_to = []
    resources = []
    config = {}

    def __init__(self, name, inputs=None, resources=None, optional=False, **config):
        #: A globally unique identifier for the block
        self.name = name

        self.inputs = inputs or {}

        self.optional = optional

        #: List of resources that this block needs
        self.resources = resources or []

        #: The config for this block
        self.config = config or {}

    async def run(self, *args, **kwargs):
        await asyncio.sleep(3600)

    async def run_while_ok(self, cluster: 'Cluster'):
        if self.running:
            return

        self.running = True
        try:
            if idiotic.node.own_block(self.name):
                await self.init_resources()

            while idiotic.node.own_block(self.name) and self.check_resources():
                await self.run()

        except KeyboardInterrupt:
            raise
        except:
            logging.exception("While running block {}".format(self.name))
        self.running = False

        if idiotic.node.own_block(self.name):
            idiotic.node.cluster.unassign_block(self.name)
            idiotic.node.cluster.assign_block(self)

    async def init_resources(self):
        while not all((r.initialized for r in self.resources)):
            await asyncio.sleep(.1)

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
        await asyncio.gather(*[asyncio.ensure_future(r.run()) for r in self.resources])

    def check_resources(self) -> bool:
        return all((r.available for r in self.resources))

    def try_resources(self):
        for r in self.resources:
            r.try_check()

    async def output(self, data, *args):
        if not args:
          args = [self.name,]
        for source in args:
            idiotic.node.dispatch({"data": data, "source": self.name+"."+source})


class InlineBlock(Block):
    def __init__(self, name, function=None, **kwargs):
        super().__init__(name, **kwargs)

        self.function = function

    def __call__(self, *args, **kwargs):
        if self.function:
            self.output(self.function(*args, **kwargs))


class ParameterBlock:
    __param_dict = {}
    __auto_params = True

    def declare_parameters(self, *keys, **items):
        self.__auto_params = False
        self.__param_dict.update(items)

        for key in keys:
            if key not in self.__param_dict:
                self.__param_dict[key] = None

    def __getattr__(self, key):
        if key in self.__param_dict:
            async def __input(val):
                await self._setparam(key, val)
            return __input
        else:
            raise ValueError("Parameter name not declared")

    async def parameter_changed(self, key, value):
        pass

    async def _setparam(self, name, value):
        self.__param_dict[name] = value
        await self.parameter_changed(name, value)

    def formatted(self, value: str):
        return value.format(**self.__param_dict)

    def get_parameter(self, key):
        return self.__param_dict.get(key)


def create(name, block_config):
    block_type = block_config.get("type", "Block")

    inputs = block_config.get("inputs", {})

    input_to = block_config.get("input_to", [])

    if isinstance(input_to, str):
        input_to = [input_to]

    requires = block_config.get("require", [])

    for attr in ("type", "inputs", "require"):
        if attr in block_config:
            del block_config[attr]

    block_cls = Block.REGISTRY[block_type]

    res = block_cls(name=name, **block_config)
    res.inputs = inputs
    res.input_to = input_to

    for req in requires:
        if req.startswith("node="):
            res.require(resource.HostResource(req[5:]))

    return res
