import collections


class MissingResource(Exception):
    pass


class Resource:
    REGISTRY = {}

    def __init__(self):
        self.running = False

    def describe(self):
        return 'resource:idiotic.Resource/'

    async def available(self):
        return bool(await self.fitness())

    async def fitness(self) -> float:
        """"Returns a number that indicates, on an arbitrary scale, how capable the executing node
        is of satisfying this resource. A larger value indicates more capability, while a falsy
        value indicates the resource is unavailable or unusable. Truthy values returned here will
        only be compared against other truthy values returned by resources of the same type.
        """
        return 1.0

    async def run(self):
        self.running = True


def create(res_config):
    if len(res_config) != 1:
        raise ValueError("Resource config is malformed; must have only one top-level config")

    res_type = list(res_config.keys())[0]
    conf = list(res_config.values())[0]

    res_cls = Resource.REGISTRY[res_type]

    if isinstance(conf, str):
        # Shorthand definition:
        # require:
        #   - RequirementType: val
        res = res_cls(conf)
    elif isinstance(conf, collections.Mapping):
        # Normal named-parameter definition:
        # require:
        #   - RequirementType:
        #     a: 1
        #     b: 2
        res = res_cls(**conf)
    elif isinstance(conf, collections.Iterable):
        # Ordered parameter definition:
        # require:
        #   - RequirementType:
        #     - 1
        #     - 2
        #     - 3
        res = res_cls(*conf)
    else:
        # I have no idea when this would actually happen
        # maybe it's binary or something?
        res = res_cls(conf)

    return res
