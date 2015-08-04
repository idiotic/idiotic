from .etc import mangle_name
from werkzeug.wrappers import Response
from flask.json import jsonify
from flask import request
import logging

LOG = logging.getLogger("idiotic.utils.api")

class _APIWrapper:
    def __init__(self, api, module, base=None):
        self.__api = api
        self.module = module
        self.modname = mangle_name(getattr(module, "MODULE_NAME", module.__name__))
        if not base:
            base = join_url("/api/module", self.modname)
        self.path = base

    def serve(self, func, path, *args, get_args=False, get_form=False, get_data=False, content_type=None, **kwargs):
        LOG.info("Adding API endpoint for {}: {} (content type {})".format(
            self.modname,
            join_url(self.path, path),
            content_type
        ))
        return self.__api.add_url_rule(join_url(self.path, path),
                                       "mod_{}_{}".format(
                                           self.modname,
                                           getattr(func, "__name__", "<unknown>")),
                                       _wrap_for_result(
                                           func, get_args, get_form,
                                           get_data, *args,
                                           content_type=content_type), **kwargs)

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
            LOG.exception("Exception encountered from API, args={}, kwargs={}".format(args, kwargs))
            return jsonify({"status": "error", "description": str(e)})
        if content_type is None:
            return jsonify({"status": "success", "result": res})
        else:
            return Response(res, mimetype=content_type)
    return wrapper

def join_url(*paths):
    return '/' + '/'.join((p.strip('/') for p in paths if p != '/'))
