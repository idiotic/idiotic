from idiotic.resource import Resource
from idiotic import node


class NodeName(Resource):
    def __init__(self, name=None, *names):
        super().__init__()

        if name:
            self.allowed_nodes = [name]
        else:
            self.allowed_nodes = names
        self.current_node = node.name

    def describe(self):
        return 'host.NodeName/' + '.'.join(sorted(self.allowed_nodes))

    async def fitness(self):
        return self.current_node in self.allowed_nodes
