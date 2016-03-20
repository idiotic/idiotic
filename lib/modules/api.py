"""api -- built-in API

"""

import logging
from idiotic.utils import jsonified, single_args
from flask import request

MODULE_NAME = "api"

log = logging.getLogger("module.api")

def configure(global_config, config, api, assets):
    api.serve(scene_command, '/api/scene/<name>/command/<command>')
    api.serve(item_command, '/api/item/<name>/command/<command>', get_args="args")
    api.serve(item_state, '/api/item/<name>/state', get_data="state",
              methods=['GET', 'PUT', 'POST'])
    api.serve(item_enable, '/api/item/<name>/enable')
    api.serve(item_disable, '/api/item/<name>/disable')
    api.serve(list_items, '/api/items')
    api.serve(list_scenes, '/api/scenes')
    api.serve(item_info, '/api/item/<name>')

def scene_command(name, command, *_, **__):
    try:
        scene = scenes[name]
        if command == "enter":
            scene.enter()
        elif command == "exit":
            scene.exit()
        else:
            raise ValueError("{} has no command {}".format(scene, command))
        return bool(scene)
    except AttributeError:
        raise ValueError("Scene '{}' does not exist!".format(name))

def item_command(name, command, args={}, *_, **kwargs):
    try:
        item = items[name]
        item.command(command, **args)
        return dict(item=item)
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

def item_state(name, state=None, *args, **kwargs):
    try:
        item = items[name]
        if state:
            if isinstance(state, bytes):
                state = state.decode('UTF-8')
            item.state = state
            #item._set_state_from_context(state, "api")
        return item.state
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

def item_enable(name, *args, **kwargs):
    try:
        item = items[name]
        item.enable()
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

def item_disable(name, *args, **kwargs):
    try:
        item = items[name]
        item.disable()
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

def list_items(*_, **__):
    return [i.json() for i in items.all()]

def list_scenes():
    return [s.json() for s in scenes.all()]

def item_info(name=None, source=None):
    if name:
        return items[name].json()
