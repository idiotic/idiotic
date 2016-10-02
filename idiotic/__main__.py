#!/usr/bin/env python3
from idiotic import config
from idiotic.cluster import Cluster, Node
from idiotic.block import Block
import idiotic
from sys import argv

import asyncio

import logging


def all_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from all_subclasses(subclass)
        yield subclass


def main():
    logging.basicConfig(style='{', level=logging.DEBUG)
    conf = config.Config.load(argv[1])
    config.config = conf
    cluster = Cluster(conf)

    node = Node((argv[2] if len(argv) > 2 else None) or conf.hostname, cluster, conf)

    idiotic.node = node

    # Here is where we would load modules
    Block.REGISTRY['Block'] = Block
    for sub in all_subclasses(Block):
        Block.REGISTRY[sub.__name__] = sub

    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.run())


if __name__ == "__main__":
    main()
