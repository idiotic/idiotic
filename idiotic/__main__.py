#!/usr/bin/env python3
from idiotic import config
from idiotic.cluster import Cluster, Node
from sys import argv

import asyncio

import logging


def main():
    logging.basicConfig(style='{', level=logging.DEBUG)
    conf = config.Config.load(argv[1])
    config.config = conf
    cluster = Cluster(conf)

    node = Node((argv[2] if len(argv) > 2 else None) or conf.hostname, cluster, conf)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(node.run())


if __name__ == "__main__":
    main()
