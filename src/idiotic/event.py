import logging
import json

log = logging.getLogger("idiotic.event")

def pack_event(event):
    try:
        return json.dumps(event.pack()).encode('UTF-8')
    except AttributeError:
        try:
            return json.dumps(event.__dict__.update({
                '__class__': type(event).__name__,
                '__owner__': getattr(event, 'MODULE', 'unknown'),
                '_remote': True,
            })).encode('UTF-8')
        except AttributeError:
            log.warn("Unable to pack event {} (type '{}') from module '{}'".format(
                str(event), type(event).__name__,
                getattr(event, 'MODULE', 'unknown')))
            return json.dumps({'__class__': type(event).__name__}).encode('UTF-8')

def unpack_event(data, modules):
    obj = json.loads(data.decode('UTF-8'))
    if '__owner__' in obj:
        owner = obj['__owner__']
        del obj['__owner__']

    if '__class__' in obj:
        clsname = obj['__class__']
        del obj['__class__']

    if owner == 'idiotic':
        cls = eval(clsname)
    else:
        cls = getattr(getattr(modules, owner), clsname)

    if cls is not None:
        return cls.unpack(obj)

class BaseEvent:
    @classmethod
    def unpack(cls, data):
        self = cls.__new__(cls)
        self.__dict__.update(data)
        return self

    def __init__(self):
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def pack(self):
        res = {'__class__': type(self).__name__,
                '__owner__': getattr(self, 'MODULE', 'unknown')}
        res.update(self.__dict__)
        return json.dumps(res).encode('UTF-8')

class StateChangeEvent(BaseEvent):
    MODULE = 'idiotic'
    def __init__(self, item, old, new, source, kind):
        super().__init__()
        self.item = item
        self.old = old
        self.new = new
        self.source = source
        self.kind = kind
        self.canceled = False

    def __repr__(self):
        return "StateChangeEvent({0.kind}, {0.old} -> {0.new} on {0.item} from {0.source})".format(self)

class CommandEvent(BaseEvent):
    def __init__(self, item, command, source, kind):
        self.item = item
        self.command = command
        self.source = source
        self.kind = kind
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def __repr__(self):
        return "CommandEvent({0.kind}, '{0.command}' on {0.item} from {0.source})".format(self)

class SceneEvent(BaseEvent):
    def __init__(self, scene, state, kind):
        self.scene = scene
        self.state = state
        self.kind = kind
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def __repr__(self):
        return "SceneEvent({0.kind} {1} scene '{0.scene}'".format(self, "enter" if self.state else "leave")

class EventFilter:
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
                    return None
        return cur

    def __str__(self):
        return "EventFilter({})".format(", ".join(self.checks_def))

    def __repr__(self):
        return "EventFilter({})".format(", ".join(
            ("{}=<{}>".format(k.replace("__","."),repr(v)) for k,v in self.checks_def.items())))
