import schedule
import time
import asyncio
from idiotic.dispatch import Dispatcher

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

def _register_module(module):
    global _modules

    if hasattr(module, "MODULE_NAME"):
        name = module.MODULE_NAME
    else:
        name = _mangle_name(module.__name__)
    _modules[name] = module

    if hasattr(module, "configure"):
        print("Configuring module {}".format(name))
        if "modules" in config and name in config["modules"]:
            module.configure(config["modules"][name])
