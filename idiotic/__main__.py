#!/usr/bin/env python3
from idiotic import config, set_node
from idiotic.cluster import Cluster, Node
from idiotic.block import Block
from sys import argv

import asyncio

import logging

import importlib
import pkgutil


def all_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from all_subclasses(subclass)
        yield subclass


def import_submodules(package, recursive=True):
    """ Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


def main():
    logging.basicConfig(style='{', level=logging.DEBUG-1)
    conf = config.Config.load(argv[1])
    config.config = conf
    cluster = Cluster(conf)

    node = Node((argv[2] if len(argv) > 2 else None) or conf.hostname, cluster, conf)

    set_node(node)

    # Recursively load everything from utils so that we get all the block types registered
    import_submodules('idiotic.util')

    # Add all the subclasses to the registry
    Block.REGISTRY['Block'] = Block
    for sub in all_subclasses(Block):
        Block.REGISTRY[sub.__name__] = sub

    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.initialize_blocks())
    loop.run_until_complete(node.run())


if __name__ == "__main__":
    main()
