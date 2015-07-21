import threading
import schedule
import asyncio
import logging
import time
from flask import Flask, json, request, Response
from .utils import AttrDict, TaggedDict, mangle_name, join_url, _APIWrapper
from .dispatch import Dispatcher

LOG = logging.getLogger("idiotic.init")

config = {}

items = TaggedDict()

scenes = TaggedDict()

modules = AttrDict()

_distribs = AttrDict()

_persistences = AttrDict()

scheduler = schedule.Scheduler()

dispatcher = Dispatcher()

persist_instance = None

distribution = None
distrib_thread = None

api = Flask(__name__)

# Monkeypatch schedule so nobody has to deal with it directly
def __sched_job_do_once(self, func, *args, **kwargs):
    self.do(lambda: func(*args, **kwargs) and schedule.CancelJob or schedule.CancelJob)

def __sched_job_do_now(self, func, *args, **kwargs):
    func(*args, **kwargs)
    self.do(func, *args, **kwargs)

schedule.Job.do_once = __sched_job_do_once
schedule.Job.do_now = __sched_job_do_now

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
            LOG.exception("Exception in scheduler.run_pending()")
            yield from asyncio.sleep(1)

def _set_config(conf):
    config.update(conf)

def _register_item(item):
    items._set(item.name, item)

def _register_scene(name, scene):
    scenes._set(name, scene)

def _register_distrib(name, distrib):
    _distribs._set(name, distrib)

def _register_persistence(name, cls):
    _persistences._set(name, cls)

def _register_module(module, assets=None):
    name = mangle_name(getattr(module, "MODULE_NAME", module.__name__))

    if config.get("modules", {}).get(name, {}).get("disable", False):
        LOG.info("Module {} is disabled; skipping registration".format(name))
        return

    if hasattr(module, "configure"):
        LOG.info("Configuring module {}".format(name))
        module.configure(
            config.get("modules", {}).get(name, {}),
            _APIWrapper(api, module, config.get(
                "modules", {}
            ).get(name, {}).get("api_base", None)),
            assets)

    modules._set(name, module)

def _register_builtin_module(module, assets=None):
    name = mangle_name(getattr(module, "MODULE_NAME", module.__name__))

    if hasattr(module, "configure"):
        LOG.info("Configuring system module {}".format(name))
        module.configure(config,
                         config.get(name, {}),
                         _APIWrapper(api, module, "/"),
                         assets)

    modules._set(name, module)

def _send_event(evt):
    LOG.debug("_send_event!")
    distribution.send(event.pack_event(evt))

def _recv_event(evt):
    LOG.debug("_recv_event!")
    dispatcher.dispatch(event.unpack_event(evt, modules))

def _start_distrib(dist, host, conf):
    global distribution, distrib_thread

    try:
        dist_cls = _distribs[dist]
    except NameError as e:
        raise NameError("Could not find distribution method {}".format(dist), e)
    distribution = dist_cls(host, conf)
    distribution.connect()

    dispatcher.bind(_send_event, utils.Filter(not_hasattr='_remote'))
    distribution.receive(_recv_event)

    thread = threading.Thread(target=distribution.run, daemon=True)
    thread.start()

def _stop_distrib():
    if distribution:
        distribution.disconnect()

    if distrib_thread:
        distrib_thread.join()

def _start_persistence(pers_cls, conf):
    global persist_instance
    persist_instance = pers_cls(conf)
    persist_instance.connect()

def _stop_persistence():
    if persist_instance:
        persist_instance.sync()
        persist_instance.disconnect()
