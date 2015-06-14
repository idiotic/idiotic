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
import socket
import asyncio
import logging
import schedule
import threading
import aiohttp.wsgi
from idiotic import utils, item, items, rule, distrib, dispatcher, run_scheduled_jobs, scheduler, _register_module, _register_builtin_module, _set_config, _start_distrib, modules, api, event

log = logging.getLogger("idiotic.main")

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

distrib_instance = None
name = socket.gethostname()
waiter = None
config = {}

def init():
    global waiter
    # Our non-daemon threads will wait on this
    waiter = ShutdownWaiter()

    # load command-line options
    arguments = docopt.docopt(__doc__, version="Current version")

    # All these dashes are stupid
    arguments = {k.lstrip('--'): v for k,v in arguments.items()}
    # A little strange, but this should work correctly for everything.
    arguments = {k: os.path.join(arguments["base"],v.replace("<base>/","")) if type(v) is str and "<base>" in v else v for k,v in arguments.items()}

    # load configuration
    global config
    global name
    logging.basicConfig(level=max(0, 5-arguments["verbose"]))
    try:
        with open(arguments["config"]) as conf_file:
            config = json.load(conf_file)

            if "name" in config:
                name = config["name"]

            if "modules" in config:
                config["modules"].update({"builtin": {"api_base": "/"}})
            else:
                config["modules"] = {"builtin": {"api_base": "/"}}

            _set_config(config)
    except (OSError, IOError) as e:
        log.exception("Could not load config file {}:".format(arguments["config"]))

    # load modules
    log.info("Loading modules from {}".format(arguments["modules"]))
    for module in utils.load_dir(arguments["modules"]):
        if module.__name__.startswith("_"):
            _register_builtin_module(module)
        else:
            _register_module(module)

    # load items
    log.info("Loading items from {}".format(arguments["items"]))
    utils.load_dir(arguments["items"])

    # load rules
    log.info("Loading rules from {}".format(arguments["rules"]))
    utils.load_dir(arguments["rules"])

    for module in modules.all(lambda m:hasattr(m, "ready")):
        module.ready()
    # load ui
    # read database

    # correspond with other instances?
    if "distribution" in config and config["distribution"]:
        log.info("Initializing distribution system...")
        if "method" in config["distribution"]:
            # Built-in methods go here
            methods = {
                "amqp": distrib.amqp,
                "udp": distrib.udp,
            }
            log.debug("Searching for module {}...".format(config["distribution"]["method"]))
            if config["distribution"]["method"] in methods:
                distrib_module = methods[config["distribution"]["method"]]
            else:
                distrib_module = getattr(modules, config["distribution"]["method"], None)

            if distrib_module and hasattr(distrib_module, "METHOD"):
                distrib_class = getattr(distrib_module, "METHOD")
                global distrib_instance
                distrib_instance, thread = _start_distrib(distrib_class, name, config["distribution"])
                waiter.threads.append(thread)
                dispatcher.bind(lambda e:distrib_instance.send(event.pack_event(e)), event.EventFilter(not_hasattr='_remote'))
                distrib_instance.receive(lambda e:dispatcher.dispatch(event.unpack_event(e, modules)))
            else:
                log.error("Could not locate distribution method '{}' -- check spelling?".format(config["distribution"]["method"]))
        else:
            log.warn("No distribution method defined. Skipping.")
    else:
        log.info("Not setting up distribution.")

    # start running updates / bindings

    # start running rules
    # start serving API
    # start serving UI

    # cleanup stuff!

def shutdown():
    if distrib_instance:
        distrib_instance.stop()
        distrib_instance.disconnect()
    waiter.join_all()
    logging.shutdown()

@asyncio.coroutine
def run_everything(*things):
    while True:
        for c in things:
            yield from c()
        yield from asyncio.sleep(.01)

if __name__ == '__main__':
    init()

    try:
        loop = asyncio.get_event_loop()
        server = loop.create_server(lambda: aiohttp.wsgi.WSGIServerHttpProtocol(api, readpayload=True), config.get("api", {}).get("listen", "*"), config.get("api", {}).get("port", 5000))
        loop.run_until_complete(asyncio.gather(run_scheduled_jobs(),
                                               server,
                                               dispatcher.run()))
    except KeyboardInterrupt:
        log.info("Shutting down")
        shutdown()
