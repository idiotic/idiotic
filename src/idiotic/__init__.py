import schedule
import time
import asyncio
from flask import Flask, json, request, Response
from idiotic.dispatch import Dispatcher
import logging
import threading

log = logging.getLogger("idiotic.init")

class ItemsProxy:
    def __init__(self, item_dict):
        self.__items = item_dict

    def with_tags(self, tags):
        ts = set(tags)
        return self.all(mask=lambda i:ts.issubset(i.tags))

    def all(self, mask=lambda _:True):
        return filter(mask, self.__items.values())

    def __getattr__(self, name):
        if name in self.__items:
            return self.__items[name]
        else:
            raise NameError("Item {} does not exist.".format(name))

    def __contains__(self, k):
        return k in self.__items

class ModulesProxy:
    def __init__(self, module_dict):
        self.__modules = module_dict

    def all(self, mask=lambda _:True):
        return filter(mask, self.__modules.values())

    def __getattr__(self, name, default=NameError):
        if name in self.__modules:
            return self.__modules[name]
        else:
            if default is NameError:
                raise NameError("Module {} not found.".format(name))
            else:
                return default

    def __contains__(self, k):
        return k in self.__modules

class ScenesProxy:
    def __init__(self, scene_dict):
        self.__scenes = scene_dict

    def all(self, mask=lambda _:True):
        return filter(mask, self.__scenes.values())

    def __getattr__(self, name, default=NameError):
        if name in self.__scenes:
            return self.__scenes[name]
        else:
            if default is NameError:
                raise NameError("Scene {} not found.".format(name))
            else:
                return default

    def __contains__(self, k):
        return k in self.__scenes


config = {}

_items = {}
items = ItemsProxy(_items)

_scenes = {}
scenes = ScenesProxy(_scenes)

_rules = {}

_modules = {}
modules = ModulesProxy(_modules)

scheduler = schedule.Scheduler()

dispatcher = Dispatcher()

distribution = None

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
            runnable_jobs = sorted((job for job in scheduler.jobs if job.should_run))
            if len(runnable_jobs):
                for job in runnable_jobs:
                    yield from asyncio.coroutine(scheduler._run_job)(job)
            else:
                yield from asyncio.sleep(1)
        except:
            log.exception("Exception in scheduler.run_pending()")
            yield from asyncio.sleep(1)

def _set_config(conf):
    global config
    config.update(conf)

def _mangle_name(name):
    return ''.join(filter(lambda x:x.isalnum() or x=='_', name.lower().replace(" ", "_"))) if name else ""

def _register_item(item):
    global _items
    _items[_mangle_name(item.name)] = item

def _register_scene(name, scene):
    global _scenes
    _scenes[_mangle_name(name)] = scene

def _join_url(*paths):
    return '/' + '/'.join((p.strip('/') for p in paths if p != '/'))

def _wrap_for_result(func, get_args, get_form, get_data, no_source=False, content_type=None, *args, **kwargs):
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

            if not no_source:
                kwargs["source"] = "api"

            res = func(*args, **kwargs)
        except Exception as e:
            log.exception("Exception encountered from API, args={}, kwargs={}".format(args, kwargs))
            return json.jsonify({"status": "error", "description": str(e)})
        if content_type is None:
            return json.jsonify({"status": "success", "result": res})
        else:
            return Response(res, mimetype=content_type)
    return wrapper

class _API:
    def __init__(self, module, base=None):
        self.module = module
        self.modname = _mangle_name(getattr(module, "MODULE_NAME", module.__name__))
        if not base:
            base = _join_url("/api/module", self.modname)
        self.path = base

    def serve(self, func, path, *args, get_args=False, get_form=False, get_data=False, content_type=None, **kwargs):
        log.info("Adding API endpoint for {}: {} (content type {})".format(
            self.modname,
            _join_url(self.path, path),
            content_type
        ))
        return api.add_url_rule(_join_url(self.path, path),
                                "mod_{}_{}".format(self.modname,
                                                   getattr(func, "__name__", "<unknown>")),
                                _wrap_for_result(func, get_args, get_form, get_data, content_type=content_type))
def _register_module(module, assets=None):
    name = _mangle_name(getattr(module, "MODULE_NAME", module.__name__))

    if config.get("modules", {}).get(name, {}).get("disable", False):
        log.info("Module {} is disabled; skipping registration".format(name))
        return

    if hasattr(module, "configure"):
        log.info("Configuring module {}".format(name))
        module.configure(config.get("modules", {}).get(name, {}),
                         _API(module, config.get("modules", {}).get(name, {}).get("api_base", None)),
                         assets)

    global _modules
    _modules[name] = module

def _register_builtin_module(module, assets=None):
    name = _mangle_name(getattr(module, "MODULE_NAME", module.__name__))

    if hasattr(module, "configure"):
        log.info("Configuring system module {}".format(name))
        module.configure(config,
                         config.get(name, {}),
                         _API(module, "/"),
                         assets)

    global _modules
    _modules[name] = module

def _start_distrib(dist_cls, host, conf):
    global distribution
    distribution = dist_cls(host, conf)
    distribution.connect()
    thread = threading.Thread(target=distribution.run, daemon=True)
    thread.start()

    return distribution, thread
