#!/usr/bin/env python3
from idiotic import config, set_node
from idiotic.cluster import Cluster, Node

import asyncio

import logging

import importlib
import pkgutil

import optparse
import time
import sys


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
    parser = optparse.OptionParser(usage="usage: %prog [options] [node-name=HOSTNAME]")
    parser.add_option("-c", "--config", dest="config", help="load config from FILE", metavar="FILE")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="enable verbose logging")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true", help="suppress output")
    (options, args) = parser.parse_args()

    log_level = logging.INFO
    if options.verbose:
        log_level = logging.DEBUG
    elif options.quiet:
        log_level = logging.ERROR

    if not options.config:
        print("No config file specified!", file=sys.stderr)
        exit(1)

    logging.basicConfig(style='{', level=log_level)

    conf = config.Config.load(options.config)

    conf._node_name = args[0] if len(args) > 0 else None

    config.config = conf
    cluster = Cluster(conf)

    logging.debug("Waiting for cluster to become ready...")
    while not cluster.ready():
        time.sleep(5)

    logging.debug("Cluster is ready!")

    node = Node(conf.nodename, cluster, conf)

    set_node(node)

    from idiotic.block import Block
    from idiotic.resource import Resource

    # Recursively load everything from utils so that we get all the block and resource types registered
    IDIOTIC_STDLIB = 'idiotic.util'
    IDIOTIC_STDLIB_BLOCKS = IDIOTIC_STDLIB + '.blocks'
    IDIOTIC_STDLIB_RESOURCES = IDIOTIC_STDLIB + '.resources'
    import_submodules(IDIOTIC_STDLIB)

    # Add all the resources to the registry
    Resource.REGISTRY['Resource'] = Resource
    for sub in all_subclasses(Resource):

        key = '.'.join((sub.__module__, sub.__name__))
        if key.startswith(IDIOTIC_STDLIB_RESOURCES + '.'):
            key = key[len(IDIOTIC_STDLIB_RESOURCES + '.'):]

        logging.debug("Loaded resource %s", key)

        Resource.REGISTRY[key] = sub

    # Add all the subclasses to the registry
    Block.REGISTRY['Block'] = Block
    for sub in all_subclasses(Block):
        logging.debug("Loaded block %s", sub.__name__)
        Block.REGISTRY[sub.__name__] = sub

    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.initialize_blocks())
    loop.run_until_complete(node.run())


if __name__ == "__main__":
    main()
