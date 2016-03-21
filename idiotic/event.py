import datetime
import logging
import json
from .utils import IdioticEncoder

LOG = logging.getLogger("idiotic.event")

def pack_event(event):
    try:
        packed = {'__class__': type(event).__name__,
                  '__owner__': getattr(event, 'MODULE', 'unknown'),
                  '__kind__': 'event',
                  '_remote': True}
        packed.update(event.pack())
        return json.dumps(packed, cls=IdioticEncoder).encode('UTF-8')
    except AttributeError:
        try:
            packed = {
                '__class__': type(event).__name__,
                '__owner__': getattr(event, 'MODULE', 'unknown'),
                '_remote': True
            }
            packed.update(dict(event.__dict__))
            return json.dumps(packed, cls=IdioticEncoder).encode('UTF-8')
        except AttributeError:
            LOG.warn("Unable to pack event {} (type '{}') from module '{}'".format(
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
        cls = getattr(modules[owner], clsname)

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
        self.time = datetime.datetime.now()

    def cancel(self):
        self.canceled = True

    def pack(self):
        res = {'__class__': type(self).__name__,
               '__owner__': getattr(self, 'MODULE', 'unknown'),
               '__kind__': 'event'}
        res.update(self.__dict__)
        return res

class SendStateChangeEvent(BaseEvent):
    MODULE = 'idiotic'
    def __init__(self, item, new, source):
        super().__init__()
        self.item = item
        self.new = new
        self.source = source

    def cancel(self):
        pass

class StateChangeEvent(BaseEvent):
    MODULE = 'idiotic'
    def __init__(self, item, old, new, source, kind):
        super().__init__()
        self.item = item
        self.old = old
        self.new = new
        self.source = source
        self.kind = kind

    def __repr__(self):
        return "StateChangeEvent({0.kind}, {0.old} -> {0.new} on {0.item} from {0.source})".format(self)

class SendCommandEvent(BaseEvent):
    MODULE = 'idiotic'
    def __init__(self, item, command, source="rule"):
        super().__init__()
        self.item = item
        self.command = command
        self.source = source

    def cancel(self):
        pass

class CommandEvent(BaseEvent):
    MODULE = 'idiotic'
    def __init__(self, item, command, source, kind, args=[], kwargs={}):
        super().__init__()
        self.item = item
        self.command = command
        self.source = source
        self.kind = kind
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "CommandEvent({0.kind}, '{0.command}' on {0.item} from {0.source})".format(self)

class SceneEvent(BaseEvent):
    MODULE = 'idiotic'
    def __init__(self, scene, state, kind):
        super().__init__()
        self.scene = scene
        self.state = state
        self.kind = kind

    def __repr__(self):
        return "SceneEvent({0.kind} {1} {0.scene}".format(self, "enter" if self.state else "leave")
