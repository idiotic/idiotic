"""api -- built-in API

"""

import logging
from idiotic.utils import jsonified, single_args
from flask import request

MODULE_NAME = "api"

log = logging.getLogger("module.api")

def configure(global_config, config, api, assets):
    api.add_url_rule('/api/scene/<name>/command/<command>', 'scene_command', scene_command)
    api.add_url_rule('/api/item/<name>/command/<command>', 'item_command', item_command)
    api.add_url_rule('/api/item/<name>/state', 'item_state', item_state, methods=['GET', 'PUT', 'POST'])
    api.add_url_rule('/api/item/<name>/enable', 'item_enable', item_enable)
    api.add_url_rule('/api/item/<name>/disable', 'item_disable', item_disable)
    api.add_url_rule('/api/items', 'list_items', list_items)
    api.add_url_rule('/api/scenes', 'list_scenes', list_scenes)
    api.add_url_rule('/api/item/<name>', 'item_info', item_info)

@jsonified
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

@jsonified
def item_command(name, command, *_, **kwargs):
    args = single_args(request.args)
    try:
        item = items[name]
        item.command(command, **args)
        return dict(item=item)
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

@jsonified
def item_state(name, *args, **kwargs):
    state = request.data
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

@jsonified
def item_enable(name, *args, **kwargs):
    try:
        item = items[name]
        item.enable()
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

@jsonified
def item_disable(name, *args, **kwargs):
    try:
        item = items[name]
        item.disable()
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

@jsonified
def list_items(*_, **__):
    return [i.json() for i in items.all()]

@jsonified
def list_scenes():
    return [s.json() for s in scenes.all()]

@jsonified
def item_info(name=None, source=None):
    if name:
        return items[name].json()
