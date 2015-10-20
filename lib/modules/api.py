"""api -- built-in API

"""

import logging
from idiotic import items, scenes

MODULE_NAME = "api"

log = logging.getLogger("module.api")

def configure(global_config, config, api, assets):
    api.serve(scene_command, '/api/scene/<name>/command/<command>')
    api.serve(item_command, '/api/item/<name>/command/<command>', get_args="args")
    api.serve(item_state, '/api/item/<name>/state', get_data="state",
              methods=['GET', 'PUT', 'POST'])
    api.serve(item_enable, '/api/item/<name>/enable')
    api.serve(item_disable, '/api/item/<name>/disable')

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
    except:
        raise ValueError("Item '{}' does not exist!".format(name))

def item_state(name, state=None, *args, **kwargs):
    try:
        item = items[name]
        if state:
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
