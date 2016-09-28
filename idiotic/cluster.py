import pysyncobj
import asyncio
from typing import Iterable


class Cluster(pysyncobj.SyncObj):
    def __init__(self, config: 'idiotic.config.Config'):
        super(Cluster, self).__init__(config.hostname, config.connect)
        self.config = config
        self.block_owners = {}
        self.resources = {}
        self.jobs = []