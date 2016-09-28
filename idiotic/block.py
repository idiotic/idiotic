import functools
from typing import Iterable


class Block:
    def __init__(self, resources: Iterable['idiotic.cluster.Resource'] = None):
        #: Map of inputs to their callbacks
        self.inputs = {}

        #: List of resources that this block needs
        self.resources = resources or []

    def require(self, *resources: 'idiotic.cluster.Resource'):
        self.resources.extend(resources)

    def check_resources(self) -> bool:
        return all((r.available for r in self.resources))

    def try_resources(self):
        for r in self.resources:
            r.try_check()
