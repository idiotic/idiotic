from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, PickleType, ForeignKey, create_engine, select
import logging
import idiotic.persistence

LOG = logging.getLogger("modules.sql")

class SQLPersistence(idiotic.persistence.Persistence):
    NAME = 'sql'
    def __init__(self, config):
        if not config:
            config = {}

        self.engine = create_engine(config.get("engine", "sqlite:///:memory:"))
        self.connection = None

        self.connect_args = config.get("parameters", {})

        self.metadata = MetaData()
        self.items = Table(
            'items', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(128), unique=True)
        )

        self.states = Table(
            'states', self.metadata,
            Column('item_id', None, ForeignKey('items.id')),
            Column('timestamp', DateTime),
            Column('value', PickleType)
        )

        self.commands = Table(
            'commands', self.metadata,
            Column('item_id', None, ForeignKey('items.id')),
            Column('timestamp', DateTime),
            Column('name', String(128)),
            Column('args', PickleType)
        )

        self.create()

    def create(self):
        self.metadata.create_all(self.engine)

    def version(self):
        return 1

    def get_item_history(self, item, kind="state", since=None, count=None):
        with self.engine.connect() as conn:
            if kind == "state":
                stmt = select(
                    [self.states.c.value, self.states.c.timestamp]
                ).select_from(
                    self.states.join(
                        self.items,
                        self.states.c.item_id == self.items.c.id
                    )
                ).where(
                    and_(self.items.c.name == item.name,
                         self.items.c.id != None)
                )

                if since:
                    stmt = stmt.where(self.states.c.timestamp > since)

                stmt = stmt.order_by(self.states.c.timestamp)

                if count:
                    stmt = stmt.limit(count)

                for row in conn.execute(stmt):
                    yield (row[0], row[1])

            elif kind == "command":
                return []

    def append_item_history(self, item, time, value, kind="state", extra=None):
        with self.engine.connect() as conn:
            results = conn.execute(
                self.items.select(
                    self.items.c.id
                ).where(
                    and_(self.items.c.name == item.name,
                         self.items.c.id != None)
                ).limit(1)
            )

            item_id = results.scalar()

            if not item_id:
                ins = conn.execute(
                    self.items.insert(), name=item.name
                )
                item_id = ins.inserted_primary_key[0]

            conn.execute(
                self.states.insert().values(
                    item_id=item_id, timestamp=time, value=value
                )
            )
