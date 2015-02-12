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

class BindingProxy:
    def __init__(self, binding_dict):
        self.__bindings = binding_dict

    def __getattr__(self, name):
        if name in self.__bindings:
            return self.__bindings[name]
        else:
            raise NameError("Binding {} not found.".format(name))

_items = {}
items = ItemProxy(_items)

_rules = {}

_bindings = {}
binding = BindingProxy(_bindings)

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
        yield from asyncio.sleep(scheduler.idle_seconds / 2)

def _scheduler_thread():
    while True:
        try:
            scheduler.run_pending()
        except:
            pass
        finally:
            time.sleep(scheduler.idle_seconds / 2)
        
def _mangle_name(name):
    # TODO regex replace things other than spaces
    out = name.lower().replace(" ", "_") if name else ""
    return out

def _register_item(item):
    global _items
    _items[_mangle_name(item.name)] = item

def _register_binding(module):
    global _bindings
    _bindings[module.__name__] = module
    
