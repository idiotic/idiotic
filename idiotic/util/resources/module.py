from idiotic.resource import Resource
import importlib


class Module(Resource):
    def __init__(self, name=None, *names):
        super().__init__()

        if name:
            self.modules = [name]
        else:
            self.modules = names

    def describe(self):
        return 'module.Module/' + ','.join(sorted(self.modules))

    def fitness(self):
        try:
            for mod in self.modules:
                importlib.import_module(mod)
            return True
        except:
            return False
