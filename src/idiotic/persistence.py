class PersistenceType(type):
    def __init__(self, name, bases, attrs):
        if name != "Persistence":
            idiotic._register_persistence(getattr(self, "NAME", name.lower()), self)

class NotConnected(Exception):
    pass

class Persistence(metaclass=PersistenceType):
    def __init__(self, config):
        pass

    def __enter__(self):
        self.connect()

    def __exit__(self):
        self.disconnect()

    def connect(self):
        pass

    def disconnect(self):
        pass

    def create(self):
        pass

    def version(self):
        pass

    def upgrade(self, old_version, new_version):
        pass

    def sync(self):
        pass

    def purge(self):
        pass

    def get_item_history(self, item, kind="state", since=None):
        pass

    def append_item_history(self, item, time, value, kind="state", extra=None):
        pass

    def set_item_history(self, item, histories, kind="state"):
        pass
