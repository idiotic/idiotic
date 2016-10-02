#!/usr/bin/env python3
from idiotic import config
from idiotic import cluster
from sys import argv


def main():
    conf = config.Config.load(argv[1])
    config.config = conf
    __cluster = cluster.Cluster(conf)
    # TODO: the thing

if __name__ == "__main__":
    main()
