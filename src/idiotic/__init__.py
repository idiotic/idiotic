import schedule
import time
import asyncio
from flask import Flask, json
from idiotic.dispatch import Dispatcher
import logging

log = logging.getLogger("idiotic.__init__")

class ItemProxy:
    def __init__(self, item_dict):
        self.__items = item_dict

    def all(self, mask=lambda _:True):
        return filter(mask, self.__items.values())

    def __getattr__(self, name):
        if name in self.__items:
            return self.__items[name]
        else:
            raise NameError("Item {} does not exist.".format(name))

class ModuleProxy:
    def __init__(self, module_dict):
        self.__modules = module_dict

    def all(self, mask=lambda _:True):
        return filter(mask, self.__modules.values())

    def __getattr__(self, name):
        if name in self.__modules:
            return self.__modules[name]
        else:
            raise NameError("Module {} not found.".format(name))

config = {}

_items = {}
items = ItemProxy(_items)

_rules = {}

_modules = {}
modules = ModuleProxy(_modules)

scheduler = schedule.Scheduler()

dispatcher = Dispatcher()

api = Flask(__name__)

def on_before_state_change(evt):
    for listener in list(evt.item.change_listeners):
        listener(evt)

def on_after_state_change(evt):
    for listener in evt.item.change_listeners:
        listener(evt)

@asyncio.coroutine
def run_scheduled_jobs():
    while True:
        try:
            scheduler.run_pending()
        except:
            pass
        yield from asyncio.sleep(1)

def _scheduler_thread():
    while True:
        try:
            scheduler.run_pending()
        except:
            pass
        finally:
            time.sleep(scheduler.idle_seconds / 2)

def _set_config(conf):
    global config
    config.update(conf)

def _mangle_name(name):
    # TODO regex replace things other than spaces
    out = name.lower().replace(" ", "_") if name else ""
    return out

def _register_item(item):
    global _items
    _items[_mangle_name(item.name)] = item

def _join_url(*paths):
    return '/' + '/'.join((p.strip('/') for p in paths))

def _wrap_for_result(func, *args, **kwargs):
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except Exception as e:
            log.info("Exception occurred from API: {}".format(e))
            return json.jsonify({"status": "error", "description": str(e)})
        return json.jsonify({"status": "success", "result": res})
    return wrapper

class _API:
    def __init__(self, module, base=None):
        self.module = module
        self.modname = _mangle_name(getattr(module, "MODULE_NAME", module.__name__))
        if not base:
            base = _join_url("/api/module", self.modname)
        self.path = base

    def serve(self, func, path, *args, **kwargs):
        log.info("Adding API endpoint for {}: {}".format(self.modname,
                                                                   _join_url(self.path, path)))
        return api.add_url_rule(_join_url(self.path, path),
                                "mod_{}_{}".format(self.modname,
                                                   func.__name__),
                                _wrap_for_result(func))
def _register_module(module):
    name = _mangle_name(getattr(module, "MODULE_NAME", module.__name__))

    if hasattr(module, "configure"):
        print("Configuring module {}".format(name))
        if "modules" in config and name in config["modules"]:
            if "disable" in config["modules"][name] and config["modules"][name]["disable"]:
                return

            module.configure(config["modules"][name], _API(module, config["modules"][name].get("api_base", None)))

    global _modules
    _modules[name] = module
