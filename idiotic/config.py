import socket
import yaml


config = None


class Config(dict):
    connect = []
    nodes = {}
    version = 0
    _node_name = None

    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def get_rpc_url(self, node):
        return "http://{}:{}/rpc".format(node, self.nodes.get(node, {}).get('rpc_port', self.cluster["rpc_port"]))

    def connect_hosts(self):
        for name, node in self.nodes.items():
            if name == self.nodename:
                continue

            default = dict(self.cluster)
            default.update(node)
            yield (default.get('host', name), default['port'])

    @property
    def nodename(self):
        return self._node_name or self.hostname

    @property
    def hostname(self):
        return socket.gethostname()

    @property
    def cluster_host(self):
        return self.nodes[self.nodename].get('host', self.hostname)

    @property
    def cluster_port(self):
        return self.nodes[self.nodename].get('port', self.cluster.get('port', 28300))

    def save(self, path):
        with open(path) as f:
            yaml.dump(self, f)

    @classmethod
    def load(cls, path):
        try:
            with open(path) as f:
                return cls(**yaml.load(f))
        except (IOError, OSError):
            return cls()
