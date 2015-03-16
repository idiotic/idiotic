#!/usr/bin/env python3
"""idiotic Distributed Internet of Things Inhabitance Controller

Usage:
  idiotic.py --help
  idiotic.py --version
  idiotic.py [--base=<dir> | [--config=<file>] [--rules=<dir>] [--items=<dir>] [--modules=<dir>] [--ui=<dir>]] [-v | -vv | -vvv | -vvvv | -vvvvv] [-s]
  idiotic.py <test>

Options:
  -h --help           Show this text.
     --version        Print the version
  -v --verbose        Set verbosity.
  -b --base=<dir>     Path to idiotic config base directory [default: /etc/idiotic].
  -c --config=<file>  Path to idiotic config file [default: <base>/conf.json].
  -r --rules=<dir>    Path to rules config directory [default: <base>/rules].
  -i --items=<dir>    Path to items config directory [default: <base>/items].
  -m --modules=<dir>  Path to modules directory [default: <base>/modules].
  -u --ui=<dir>       Path to UI config directory [default: <base>/ui].
  -s --standalone     Run without connecting to other instances.
"""

import os
import sys
import json
import time
import docopt
import asyncio
import logging
import schedule
import threading
from idiotic import utils, item, items, rule, dispatcher, _scheduler_thread, run_scheduled_jobs, scheduler, _register_module, _set_config, modules

class ShutdownWaiter:
    def __init__(self):
        self.running = True
        self.threads = []

    def stop(self):
        self.running = False

    def join_all(self):
        self.stop()
        for thread in self.threads:
            thread.join()

    def started(self, thread):
        self.threads.append(thread)

    def __bool__(self):
        return self.running

waiter = None

def init():
    global waiter
    # load command-line options
    arguments = docopt.docopt(__doc__, version="Current version")

    # All these dashes are stupid
    arguments = {k.lstrip('--'): v for k,v in arguments.items()}
    # A little strange, but this should work correctly for everything.
    arguments = {k: os.path.join(arguments["base"],v.replace("<base>/","")) if type(v) is str and "<base>" in v else v for k,v in arguments.items()}

    # load configuration
    logging.basicConfig(level=max(0, 5-arguments["verbose"]))
    try:
        with open(arguments["config"]) as conf_file:
            config = json.load(conf_file)
            _set_config(config)
    except (OSError, IOError) as e:
        logging.warn("Could not load config file {}: {}".format(arguments["config"], e))

    # load modules
    logging.info("Loading modules from {}".format(arguments["modules"]))
    for module in utils.load_dir(arguments["modules"]):
        _register_module(module)

    # load items
    logging.info("Loading items from {}".format(arguments["items"]))
    utils.load_dir(arguments["items"])

    # load rules
    logging.info("Loading rules from {}".format(arguments["rules"]))
    utils.load_dir(arguments["rules"])

    for module in modules.all(lambda m:hasattr(m, "ready")):
        module.ready()
    # load ui
    # read database
    # correspond with other instances?
    # start running updates / bindings
    # Our non-daemon threads will wait on this
    waiter = ShutdownWaiter()

    # start running rules
    # start serving API
    # start serving UI

    # cleanup stuff!

def shutdown():
    waiter.join_all()
    logging.shutdown()

if __name__ == '__main__':
    init()

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_scheduled_jobs())
    except KeyboardInterrupt:
        print("Shutting down")
        shutdown()
