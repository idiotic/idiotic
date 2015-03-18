import schedule
import time
import asyncio
from flask import Flask, json, request
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

# Monkeypatch schedule so nobody has to deal with it directly
def __sched_job_do_once(self, func, *args, **kwargs):
    self.do(lambda: func(*args, **kwargs) and schedule.CancelJob or schedule.CancelJob)

def __sched_job_do_now(self, func, *args, **kwargs):
    func(*args, **kwargs)
    self.do(func, *args, **kwargs)

schedule.Job.do_once = __sched_job_do_once
schedule.Job.do_now = __sched_job_do_now

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
    return ''.join(filter(lambda x:x.isalnum() or x=='_', name.lower().replace(" ", "_"))) if name else ""

def _register_item(item):
    global _items
    _items[_mangle_name(item.name)] = item

def _join_url(*paths):
    return '/' + '/'.join((p.strip('/') for p in paths if p != '/'))

def _wrap_for_result(func, get_args, get_form, get_data, *args, **kwargs):
    def wrapper(*args, **kwargs):
        try:
            if get_args is True:
                kwargs.update(getattr(request, "args", {}))
            elif get_args:
                kwargs[get_args] = getattr(request, "args", {})

            if get_form is True:
                kwargs.update(getattr(request, "form", {}))
            elif get_form:
                kwargs[get_form] = getattr(request, "form", {})

            if get_data is True:
                kwargs["data"] = getattr(request, "data", "")
            elif get_data:
                kwargs[get_data] = getattr(request, "data", "")

            res = func(*args, **kwargs)
        except Exception as e:
            log.exception("Exception encountered from API, args={}, kwargs={}".format(args, kwargs))
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

    def serve(self, func, path, *args, get_args=False, get_form=False, get_data=False, **kwargs):
        log.info("Adding API endpoint for {}: {}".format(self.modname,
                                                         _join_url(self.path, path)))
        return api.add_url_rule(_join_url(self.path, path),
                                "mod_{}_{}".format(self.modname,
                                                   func.__name__),
                                _wrap_for_result(func, get_args, get_form, get_data))
def _register_module(module):
    name = _mangle_name(getattr(module, "MODULE_NAME", module.__name__))

    if config.get("modules", {}).get(name, {}).get("disable", False):
        log.info("Module {} is disabled; skipping registration".format(name))
        return

    if hasattr(module, "configure"):
        log.info("Configuring module {}".format(name))
        log.info("Config: {}".format(config))
        module.configure(config.get("modules", {}).get(name, {}), _API(module, config.get("modules", {}).get(name, {}).get("api_base", None)))

    global _modules
    _modules[name] = module
