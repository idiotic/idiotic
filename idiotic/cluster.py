import pysyncobj
from idiotic import config
from idiotic import block
from idiotic import resource


class Node:
    def __init__(self, name):
        self.name = name


class Cluster(pysyncobj.SyncObj):
    def __init__(self, configuration: config.Config):
        super(Cluster, self).__init__(configuration.hostname, configuration.connect)
        self.config = configuration
        self.block_owners = {}
        self.resources = {}
        self.jobs = []

    @pysyncobj.replicated
    def assign_block(self, block: block.Block):
        nodes = block.precheck_nodes(self.config)

        for node in nodes:
            pass
            # assign the block to the node
            # check the resources, reassign if needed
