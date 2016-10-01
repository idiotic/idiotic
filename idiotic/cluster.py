import pysyncobj
from idiotic import config
from idiotic import block
import asyncio


class Node:
    def __init__(self, name):
        self.name = name


class UnassignableBlock(Exception):
    pass

class Cluster(pysyncobj.SyncObj):
    def __init__(self, configuration: config.Config):
        super(Cluster, self).__init__(configuration.hostname, configuration.connect)
        self.config = configuration
        self.block_owners = {}
        self.block_lock = asyncio.locks.Lock()
        self.resources = {}
        self.jobs = []

    @pysyncobj.replicated
    async def assign_block(self, block: block.Block):

        with await self.block_lock:
            self.block_owners[block] = None
            nodes = await block.precheck_nodes(self.config)

            for node in nodes:
                self.block_owners[block] = node
                # Later:
                return

            raise UnassignableBlock(block)
