import logging
import imp
import sys
import os

class AttrDict:
    def __init__(self, values={}):
        self.__values = dict(values)

    def _set(self, key, value):
        self.__values[key] = value

    def all(self, filt=None):
        if isinstance(filt, Filter):
            return filter(self.__values.values(), filt.check)
        elif callable(filt):
            return filter(self.__values.values(), filt)
        else:
            return self.__values.values()

    def __getattr__(self, key):
        if key in self.__values:
            return self.__values[key]
        else:
            raise NameError("Could not find locate {}".format(key))

    def __getitem__(self, index):
        return getattr(self, mangle_name(index))

    def __contains__(self, key):
        return key in self.__values

class TaggedDict(AttrDict):
    def with_tags(self, tags):
        ts=set(tags)
        return self.all(mask=lambda i:ts.issubset(i.tags))

class Filter:
    def __init__(self, mode=None, filters=None, **kwargs):
        self.checks = []
        if mode is None:
            self.mode = lambda *x:all(*x)
        else:
            self.mode = lambda *x:mode(*x)

        if filters:
            # filters is used in case we need to use a reserved word
            # as an argument... though that should probably be avioded
            kwargs.update(filters)

        self.checks_def = kwargs

        for k, v in kwargs.items():
            # I'm very surprised I had to use a closure here. The only
            # other time I had to, I was doing some serious black
            # magic...
            def closure(k,v):
                if "__" in k:
                    key, op = k.rsplit("__", 1)
                else:
                    key, op = "", k
                path = key.split("__")

                if op == "contains":
                    self.checks.append(lambda e:v in self.__resolve_path(e, path))
                elif op == "not_contains":
                    self.checks.append(lambda e:v not in self.__resolve_path(e, path))
                elif op == "in":
                    self.checks.append(lambda e:self.__resolve_path(e, path) in v)
                elif op == "not_in":
                    self.checks.append(lambda e:self.__resolve_path(e, path) not in v)
                elif op == "is":
                    self.checks.append(lambda e:self.__resolve_path(e, path) is v)
                elif op == "is_not":
                    self.checks.append(lambda e:self.__resolve_path(e, path) is not v)
                elif op == "lt":
                    self.checks.append(lambda e:self.__resolve_path(e, path) < v)
                elif op == "gt":
                    self.checks.append(lambda e:self.__resolve_path(e, path) > v)
                elif op == "le":
                    self.checks.append(lambda e:self.__resolve_path(e, path) <= v)
                elif op == "ge":
                    self.checks.append(lambda e:self.__resolve_path(e, path) >= v)
                elif op == "ne":
                    self.checks.append(lambda e:self.__resolve_path(e, path) != v)
                elif op == "match":
                    self.checks.append(lambda e:v(self.__resolve_path(e, path)))
                elif op == "not_match":
                    self.checks.append(lambda e:not v(self.__resolve_path(e, path)))
                elif op == "eq":
                    self.checks.append(lambda e:self.__resolve_path(e, path) == v)
                elif op == "type":
                    self.checks.append(lambda e:type(self.__resolve_path(e, path)) == v)
                elif op == "type_not":
                    self.checks.append(lambda e:type(self.__resolve_path(e, path)) != v)
                elif False and op == "item":
                    # hack so we can check that the 'item' of an event by name
                    self.checks.append(functools.partial(self._item_check_hack, path, op, v))
                else:
                    # By default just check for equality
                    path.append(op)
                    self.checks.append(lambda e:self.__resolve_path(e, path) == v)
            closure(k,v)

    def check(self, event):
        res = self.mode(c(event) for c in self.checks)
        return res

    def _item_check_hack(self, path, op, v, e):
        # we can't import item because that would be rather circular
        # so instead, we can just check for the name attribute...
        # this is pretty ugly though, hopefully there's a nice
        # way around this eventually
        path.append(op)
        item = self.__resolve_path(e, path)
        if hasattr(v, "name") and hasattr(item, "name"):
            return v is item
        elif isinstance(v, str) and hasattr(item, "name"):
            return item.name == v
        elif hasattr(v, "name") and isinstance(item, str):
            return item == v.name
        else:
            return item == v

    def __resolve_path(self, e, path):
        cur = e
        for key in path:
            if key:
                try:
                    cur = getattr(cur, key)
                except AttributeError as e:
                    return None
        return cur

    def __str__(self):
        return "Filter({})".format(", ".join(self.checks_def))

    def __repr__(self):
        return "Filter({})".format(", ".join(
            ("{}=<{}>".format(k.replace("__","."),repr(v)) for k,v in self.checks_def.items())))

class _APIWrapper:
    def __init__(self, api, module, base=None):
        self.__api = api
        self.module = module
        self.modname = mangle_name(getattr(module, "MODULE_NAME", module.__name__))
        if not base:
            base = join_url("/api/module", self.modname)
        self.path = base

    def serve(self, func, path, *args, get_args=False, get_form=False, get_data=False, content_type=None, **kwargs):
        log.info("Adding API endpoint for {}: {} (content type {})".format(
            self.modname,
            join_url(self.path, path),
            content_type
        ))
        return self.__api.add_url_rule(join_url(self.path, path),
                                "mod_{}_{}".format(self.modname,
                                                   getattr(func, "__name__", "<unknown>")),
                                _wrap_for_result(func, get_args, get_form, get_data, content_type=content_type))

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

def join_url(*paths):
    return '/' + '/'.join((p.strip('/') for p in paths if p != '/'))

def mangle_name(name):
    return ''.join(filter(lambda x:x.isalnum() or x=='_', name.lower().replace(" ", "_"))) if name else ""

def load_dir(path, include_assets=False):
    sys.path.insert(0, os.path.abspath("."))
    modules = []
    for f in os.listdir(path):
        try:
            if f.startswith(".") or f.endswith("~") or f.endswith("#") or f.startswith("__"):
                continue

            logging.info("Loading file {}...".format(os.path.join(path, f)))
            name = os.path.splitext(f)[0]

            try:
                modules.append((imp.load_source(name, os.path.join(path, f)), None))
            except IsADirectoryError:
                logging.info("Attempting to load directory {} as a module...".format(
                    os.path.join(path, f)))

                try:
                    mod = imp.load_source(name, os.path.join(path, f, '__init__.py'))
                    assets = None
                    if os.path.exists(os.path.join(path, f, 'assets')) and \
                       os.path.isdir(os.path.join(path, f, 'assets')):
                        assets = os.path.abspath(os.path.join(path, f, 'assets'))

                    modules.append((mod, assets))
                except FileNotFoundError:
                    logging.error("Unable to load module {}: {} does not exist".format(
                        name, os.path.join(path, f, '__init__.py')))
        except Exception as e:
            logging.exception("Exception encountered while loading {}".format(os.path.join(path, f)))

    return modules
