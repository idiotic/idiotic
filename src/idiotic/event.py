import logging

log = logging.getLogger("idiotic.event")

class StateChangeEvent:
    def __init__(self, item, old, new, source, kind):
        self.item = item
        self.old = old
        self.new = new
        self.source = source
        self.kind = kind
        self.canceled = False

    def cancel(self):
        self.canceled = True

class CommandEvent:
    def __init__(self, item, command, source, kind):
        self.item = item
        self.command = command
        self.source = source
        self.kind = kind
        self.canceled = False

    def cancel(self):
        self.canceled = True

class EventFilter:
    def __init__(self, mode=all, filters=None, **kwargs):
        self.checks = []
        self.mode = mode # any or all

        if filters:
            # filters is used in case we need to use a reserved word
            # as an argument... though that should probably be avioded
            kwargs.update(filters)

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
                else:
                    # By default just check for equality
                    path.append(op)
                    self.checks.append(lambda e:self.__resolve_path(e, path) == v)
            closure(k,v)

    def check(self, event):
        res = self.mode(c(event) for c in self.checks)
        return res

    def __resolve_path(self, e, path):
        cur = e
        for key in path:
            if key:
                try:
                    cur = getattr(cur, key)
                except AttributeError as e:
                    log.warn("Unable to resolve path '{}' at '{}': {}".format(".".join(path), key, e))
                    return None
        return cur
