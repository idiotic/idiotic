from . import _register_persistence

class PersistenceType(type):
    def __init__(cls, name, bases, attrs):
        super(PersistenceType, cls).__init__(name, bases, attrs)
        if name != "Persistence":
            _register_persistence(getattr(cls, "NAME", name.lower()), cls)

class NotConnected(Exception):
    pass

class Persistence(metaclass=PersistenceType):
    def __init__(self, config):
        pass

    def __enter__(self):
        self.connect()

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def connect(self):
        """Establish a connection to the database, if necessary."""
        pass

    def disconnect(self):
        """Close the connection to the database, if necessary."""
        pass

    def create(self):
        """Create and initialize the database, if it does not already exist.
May be called automatically by the persistence engine if needed.

        """
        pass

    def version(self):
        """The version of the database when it was created or last updated.
"""
        pass

    def upgrade(self, old_version, new_version):
        """Convert the database from an old version to a new version."""
        pass

    def sync(self):
        """Write any uncommitted data to the underlying database engine."""
        pass

    def purge(self):
        """Delete any data that does not meet retention requirements."""
        pass

    def get_item_history(self, item, kind="state", since=None, count=-1):
        """Retrieve the history for the given item."""
        pass

    def append_item_history(self, item, time, value, kind="state", extra=None):
        pass

    def set_item_history(self, item, histories, kind="state"):
        pass
