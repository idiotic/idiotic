#!/usr/bin/env python3
from idiotic import config
from sys import argv


def main():
    conf = config.Config.load(argv[1])
    # TODO: the thing

if __name__ == "__main__":
    main()
