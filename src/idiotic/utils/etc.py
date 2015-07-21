import json

def mangle_name(name):
    return ''.join((x for x in name.lower().replace(" ", "_") if x.isalnum() or x=='_')) if name else ""

class IdioticEncoder(json.JSONEncoder):
    def __init__(self, *args, depth=-1, **kwargs):
        super().__init__(*args, **kwargs)
        self.depth = depth

    def default(self, obj):
        if obj is None:
            return "null"
        if hasattr(obj, "pack"):
            return obj.pack()
        else:
            return json.JONEncoder.default(self, obj)
