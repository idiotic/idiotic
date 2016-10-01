import socket
import yaml


config = None


class Config(dict):
    connect = []
    nodes = {}

    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @property
    def hostname(self):
        return socket.gethostname()

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
