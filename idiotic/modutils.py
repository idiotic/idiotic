from idiotic import instance, utils
import functools
import logging
import os.path

LOG = logging.getLogger("idiotic.modutils")

class ModuleNotFoundException(Exception):
    pass

def _require(kind, container, name, optional=False):
    if name in container:
        LOG.debug("_require(): Returning already-loaded module for {} {}".format(kind, container))
        return container[name]

    paths = ((instance.config["paths"]["lib"][kind], True),
             (instance.config["paths"][kind], False))

    for path, system in paths:
        try:
            LOG.debug("Trying to load {} {} from {}".format(kind, name, os.path.join(path, name + '.py')))
            module, assets = utils.load_single(os.path.join(path, name + '.py'))

            if not getattr(module, "_idiotic_loaded", False):
                instance.augment_module(module)

                real_name = utils.mangle_name(getattr(module, "MODULE_NAME", module.__name__))
            
                if kind == "module":
                    if system:
                        instance._register_builtin_module(module, assets)
                    else:
                        instance._register_module(module, assets)
                else:
                    container[real_name] = module
                    if name != real_name:
                        container[name] = module
            return module
        except FileNotFoundError:
            continue

    if optional:
        return None

    raise ModuleNotFoundException("Unable to find {} module named {} in {}. If the module's name differs from its filename, you may need to specify that instead.".format(kind, name, ':'.join(list(zip(*paths))[0])))

require_module = functools.partial(_require, "module", instance.modules)
require_rules = functools.partial(_require, "rules", instance.rule_modules)
require_items = functools.partial(_require, "items", instance.item_modules)

ALL = [require_module, require_rules, require_items]
