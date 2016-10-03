from idiotic.resource import Resource
from idiotic.config import config


class NodeIs(Resource):
    def __init__(self, node):
        self.node = node

    @property
    def available(self):
        return self.node == config.nodename()

    async def available_hosts(self, config):
        return [self.node]
