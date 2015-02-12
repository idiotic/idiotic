#!/usr/bin/env python3
"""Idiotic Distributed Internet of Things Interaction Controller

Usage:
  idiotic.py --help
  idiotic.py --version
  idiotic.py [--base=<dir> | [--config=<file>] [--rules=<dir>] [--items=<dir>] [--ui=<dir>]] [-v | -vv | -vvv | -vvvv | -vvvvv] [-s]
  idiotic.py <test>

Options:
  -h --help           Show this text.
     --version        Print the version
  -v --verbose        Set verbosity.
  -b --base=<dir>     Path to idiotic config base directory [default: /etc/idiotic].
  -c --config=<file>  Path to idiotic config file [default: <base>/conf.json].
  -r --rules=<dir>    Path to rules config directory [default: <base>/rules].
  -i --items=<dir>    Path to Item config directory [default: <base>/items].
  -u --ui=<dir>       Path to UI config directory [default: <base>/ui].
  -s --standalone     Run without connecting to other instances.
"""

import os
import sys
import docopt
import logging
import threading
import schedule
import time
from idiotic import utils, item, items, rule, dispatcher, _scheduler_thread

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

    # load items
    logging.info("Loading items from {}".format(arguments["items"]))
    utils.load_dir(arguments["items"])

    # load bindings
    # load rules
    logging.info("Loading rules from {}".format(arguments["rules"]))
    utils.load_dir(arguments["rules"])
    # load ui
    # read database
    # correspond with other instances?
    # start running updates / bindings
    # Our non-daemon threads will wait on this
    waiter = ShutdownWaiter()

    schedule_thread = threading.Thread(target=_scheduler_thread, daemon=True)
    schedule_thread.start()

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
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Shutting down")
        shutdown()
