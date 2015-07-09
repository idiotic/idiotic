import schedule
import time
import asyncio
from flask import Flask, json, request, Response
from idiotic.dispatch import Dispatcher
from idiotic.utils import AttrDict, TaggedDict
import logging
import threading

log = logging.getLogger("idiotic.init")

config = {}

items = TaggedDict()

scenes = TaggedDict()

modules = AttrDict()

_persistences = AttrDict()

_rules = {}

scheduler = schedule.Scheduler()

dispatcher = Dispatcher()

persist_instance = None

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
    items._set(item.name, item)

def _register_scene(name, scene):
    scenes._set(name, scene)

def _register_persistence(name, cls):
    _persistences._set(name, cls)

def _join_url(*paths):
    return '/' + '/'.join((p.strip('/') for p in paths if p != '/'))

def _wrap_for_result(func, get_args, get_form, get_data, no_source=False, content_type=None, *args, **kwargs):
    def wrapper(*args, **kwargs):
        try:
            clean_get_args = {k: v[0] if isinstance(v, list) else v for k, v in getattr(request, "args", {}).items()}
            if get_args is True:
                kwargs.update(clean_get_args)
            elif get_args:
                kwargs[get_args] = clean_get_args

            clean_form = {k: v[0] if isinstance(v, list) else v for k, v in getattr(request, "form", {}).items()}
            if get_form is True:
                kwargs.update(clean_form)
            elif get_form:
                kwargs[get_form] = clean_form

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

def _start_persistence(pers_cls, conf):
    global persist_instance
    persist_instance = pers_cls(conf)
    persist_instance.connect()

def _stop_persistence():
    if persist_instance:
        persist_instance.sync()
        persist_instance.disconnect()
