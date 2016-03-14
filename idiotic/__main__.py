#!/usr/bin/env python3
"""idiotic Distributed Internet of Things Inhabitance Controller

Usage:
  idiotic.py --help
  idiotic.py --version
  idiotic.py [--base=<dir> | [--config=<file>] [--rules=<dir>] [--items=<dir>] [--modules=<dir>]] [-v | -vv | -q | -qq] [-s]

Options:
  -h --help           Show this text.
     --version        Print the version
  -v --verbose        Set verbosity.
  -q --quiet          Suppress output. Use -qq to suppress even errors.
  -b --base=<dir>     Path to idiotic config base directory [default: /etc/idiotic].
  -c --config=<file>  Path to idiotic config file [default: <base>/conf.json].
  -r --rules=<dir>    Path to rules config directory [default: <base>/rules].
  -i --items=<dir>    Path to items config directory [default: <base>/items].
  -m --modules=<dir>  Path to modules directory [default: <base>/modules].
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
import threading
import aiohttp.wsgi
import idiotic
from idiotic import utils, item, rule, distrib, event
# FIXME: This is sort of a hack, due to dependency resolution order
# problems (persistence and distrib must import idiotic for the
# registration hooks). The better solution would be to move concrete
# persistence and distribution methods into a lib folder
import idiotic.persistence
#import idiotic.distrib

LOG = logging.getLogger("idiotic.main")

def init():
    # load command-line options
    arguments = docopt.docopt(__doc__, version="0.1.6")

    # All these dashes are stupid
    arguments = {k.lstrip('--'): v for k,v in arguments.items()}
    # A little strange, but this should work correctly for everything.
    arguments = {k: os.path.join(arguments["base"],v.replace("<base>/","")) if type(v) is str and "<base>" in v else v for k,v in arguments.items()}

    verbose = arguments.get("verbose", 0)
    quiet = arguments.get("quiet", 0)
    level = logging.INFO

    if verbose == 1:
        level = logging.DEBUG
    elif verbose == 2:
        level = logging.DEBUG
    elif quiet == 1:
        level = logging.ERROR
    elif quiet == 2:
        level = logging.CRITICAL + 1

    logging.basicConfig(level=level)

    config = {}
    name = socket.gethostname()

    try:
        with open(arguments["config"]) as conf_file:
            config = json.load(conf_file)

            if "name" in config:
                name = config["name"]

            if "modules" in config:
                config["modules"].update({"builtin": {"api_base": "/"}})
            else:
                config["modules"] = {"builtin": {"api_base": "/"}}

    except (OSError, IOError):
        LOG.exception("Could not load config file {}:".format(arguments["config"]))

    instance = idiotic.Idiotic(config, name)

    # FIXME global state
    idiotic.instance = instance

    # load modules
    LOG.info("Loading modules from {}".format(arguments["modules"]))
    for module, assets in utils.load_dir(arguments["modules"], True):
        instance.augment_module(module)
        if module.__name__.startswith("_"):
            instance._register_builtin_module(module, assets)
        else:
            instance._register_module(module, assets)

    # load items
    LOG.info("Loading items from {}".format(arguments["items"]))
    for module, _ in utils.load_dir(arguments["items"]):
        instance.augment_module(module)

    # load rules
    LOG.info("Loading rules from {}".format(arguments["rules"]))
    for module, _ in utils.load_dir(arguments["rules"]):
        instance.augment_module(module)

    for module in instance.modules.all(lambda m:hasattr(m, "ready")):
        module.ready()

    # correspond with other instances?
    if "distribution" in config and config["distribution"]:
        LOG.info("Initializing distribution system...")
        if "method" in config["distribution"]:
            # Built-in methods go here
            instance._start_distrib(config["distribution"]["method"],
                                   name, config["distribution"])
        else:
            LOG.warn("No distribution method specified. Skipping.")
    else:
        LOG.debug("Not setting up distribution.")

    # connect to persistence engine
    if "persistence" in config and config["persistence"]:
        LOG.info("Connecting to persistence engine...")
        if not config["persistence"].get("disabled", False):
            if "method" in config["persistence"]:
                try:
                    instance._start_persistence(config["persistence"]["method"], config["persistence"])
                except NameError as e:
                    LOG.error("Could not locate persistence engine '{}' -- check spelling?".format(config["persistence"]["method"]), e)
            else:
                LOG.warn("Persistence engine not specified. Skipping.")
        else:
            LOG.warn("Persistence is disabled.")
    else:
        LOG.info("Not setting up persistence.")

    return instance

def shutdown(instance):
    instance._stop_distrib()

    instance._stop_persistence()

    logging.shutdown()

@asyncio.coroutine
def run_everything(*things):
    while True:
        for c in things:
            yield from c()
        yield from asyncio.sleep(.01)

def main():
    instance = init()

    try:
        loop = asyncio.get_event_loop()

        api_config = instance.config.get("api", {})
        listen = api_config.get("listen", "*")
        port = api_config.get("port", 5000)

        # FIXME find out why this is necessary
        instance._finalize_api()

        server = loop.create_server(lambda: aiohttp.wsgi.WSGIServerHttpProtocol(instance.api, readpayload=True), listen, port)
        loop.run_until_complete(asyncio.gather(instance.run_scheduled_jobs(),
                                               server,
                                               instance.dispatcher.run()))
    except KeyboardInterrupt:
        LOG.info("Shutting down")
        shutdown(instance)

if __name__ == '__main__':
    main()
