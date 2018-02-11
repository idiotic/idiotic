#!/usr/bin/env python3

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Text, Float, Enum
from sqlalchemy import create_engine
from sqlalchemy.sql import select, bindparam, and_, or_, not_
import datetime
import time

from idiotic.config import config as global_config
from idiotic import resource, block
import logging
import asyncio

log = logging.getLogger(__name__)


metadata = MetaData()

monitors = Table('Monitors', metadata,
                 Column('Id', Integer, primary_key=True, autoincrement=True, nullable=False),
                 Column('Name', String(64), nullable=False, default=''),
                 Column('ServerId', Integer, nullable=False, default=None),
                 Column('Type', Enum('Local','Remote','File','Ffmpeg','Libvlc','cURL'), nullable=False, default='Local'),
                 Column('Function', Enum('None','Monitor','Modect','Record','Mocord','Nodect'), nullable=False, default='Monitor'),
                 Column('Enabled', Integer, nullable=False, default=1),
                 Column('LinkedMonitors', String(255), nullable=False, default=''),
                 Column('Triggers', Enum('X10'), nullable=False, default=''),
                 Column('Device', Text, nullable=False),
                 Column('Channel', Integer, nullable=False, default=0),
                 Column('Format', Integer, nullable=False, default=0),
                 Column('V4LMultiBuffer', Integer, nullable=False, default=None),
                 Column('V4LCapturesPerFrame', Integer, nullable=False, default=None),
                 Column('Protocol', String(16), nullable=False, default=''),
                 Column('Method', String(16), nullable=False, default=''),
                 Column('Host', String(64), nullable=False, default=''),
                 Column('Port', String(8), nullable=False, default=''),
                 Column('SubPath', String(64), nullable=False, default=''),
                 Column('Path', String(255), nullable=False, default=''),
                 Column('Options', String(255), nullable=False, default=''),
                 Column('User', String(64), nullable=False, default=''),
                 Column('Pass', String(64), nullable=False, default=''),
                 Column('Width', Integer, nullable=False, default=0),
                 Column('Height', Integer, nullable=False, default=0),
                 Column('Colours', Integer, nullable=False, default=1),
                 Column('Palette', Integer, nullable=False, default=0),
                 Column('Orientation', Enum('0','90','180','270','hori','vert'), nullable=False, default='0'),
                 Column('Deinterlacing', Integer, nullable=False, default=0),
                 Column('RTSPDescribe', Integer, nullable=False, default=0),
                 Column('Brightness', Integer, nullable=False, default=-1),
                 Column('Contrast', Integer, nullable=False, default=-1),
                 Column('Hue', Integer, nullable=False, default=-1),
                 Column('Colour', Integer, nullable=False, default=-1),
                 Column('EventPrefix', String(32), nullable=False, default='Event-'),
                 Column('LabelFormat', String(64), nullable=False, default='%N - %y/%m/%d %H:%M:%S'),
                 Column('LabelX', Integer, nullable=False, default=0),
                 Column('LabelY', Integer, nullable=False, default=0),
                 Column('LabelSize', Integer, nullable=False, default=1),
                 Column('ImageBufferCount', Integer, nullable=False, default=100),
                 Column('WarmupCount', Integer, nullable=False, default=25),
                 Column('PreEventCount', Integer, nullable=False, default=10),
                 Column('PostEventCount', Integer, nullable=False, default=10),
                 Column('StreamReplayBuffer', Integer, nullable=False, default=1000),
                 Column('AlarmFrameCount', Integer, nullable=False, default=1),
                 Column('SectionLength', Integer, nullable=False, default=600),
                 Column('FrameSkip', Integer, nullable=False, default=0),
                 Column('MotionFrameSkip', Integer, nullable=False, default=0),
                 Column('AnalysisFPS', Float(asdecimal=True), default=None),
                 Column('AnalysisUpdateDelay', Integer, nullable=False, default=0),
                 Column('MaxFPS', Float(asdecimal=True), default=None),
                 Column('AlarmMaxFPS', Float(asdecimal=True), nullable=True, default=None),
                 Column('FPSReportInterval', Integer, nullable=False, default=250),
                 Column('RefBlendPerc', Integer, nullable=False, default=6),
                 Column('AlarmRefBlendPerc', Integer, nullable=False, default=6),
                 Column('Controllable', Integer, nullable=False, default=0),
                 Column('ControlId', Integer, nullable=False, default=0),
                 Column('ControlDevice', String(255), nullable=True, default=None),
                 Column('ControlAddress', String(255), nullable=True, default=None),
                 Column('AutoStopTimeout', Float(asdecimal=True), nullable=True, default=None),
                 Column('TrackMotion', Integer, nullable=False, default=0),
                 Column('TrackDelay', Integer, nullable=False, default=0),
                 Column('ReturnLocation', Integer, nullable=False, default=-1),
                 Column('ReturnDelay', Integer, nullable=False, default=0),
                 Column('DefaultView', Enum('Events','Control'), nullable=False, default='Events'),
                 Column('DefaultRate', Integer, nullable=False, default=100),
                 Column('DefaultScale', Integer, nullable=False, default=100),
                 Column('SignalCheckColour', String(32), nullable=False, default='#0000BE'),
                 Column('WebColour', String(32), nullable=False, default='red'),
                 Column('Exif', Integer, nullable=False, default=0),
                 Column('Sequence', Integer, nullable=False, default=None)
)

events = Table('Events', metadata,
               Column('Id', Integer, primary_key=True),
               Column('MonitorId', None, ForeignKey('Monitors.Id'), primary_key=True),
               Column('Name', String(64), nullable=False),
               Column('Cause', String(32), nullable=False),
               Column('StartTime', DateTime, nullable=True, default=None),
               Column('EndTime', DateTime, nullable=True, default=None),
               Column('Width', Integer, nullable=False, default=0),
               Column('Height', Integer, nullable=False, default=0),
               Column('Length', Float(asdecimal=True), nullable=False, default=0.00),
               Column('Frames', Integer, nullable=True, default=None),
               Column('AlarmFrames', Integer, nullable=True, default=None),
               Column('TotScore', Integer, nullable=False, default=0),
               Column('AvgScore', Integer, nullable=True, default=0),
               Column('MaxScore', Integer, nullable=True, default=0),
               Column('Archived', Integer, nullable=False, default=0),
               Column('Videoed', Integer, nullable=False, default=0),
               Column('Uploaded', Integer, nullable=False, default=0),
               Column('Emailed', Integer, nullable=False, default=0),
               Column('Messaged', Integer, nullable=False, default=0),
               Column('Executed', Integer, nullable=False, default=0),
               Column('Notes', Text, nullable=True, default=None)
)


class ZoneMinderSql(resource.Resource):
    SERVERS = {}

    @classmethod
    def instance(cls, database, **options):
        if ('zoneminder.ZoneMinderSql/' + database) not in cls.SERVERS:
            res = cls(database, **options)
            cls.SERVERS[res.describe()] = res
            return res

        return cls.SERVERS['zoneminder.ZoneMinderSql/' + database]

    @property
    def engine(self):
        if not self._engine:
            self._engine = create_engine(self._database, echo=False, isolation_level="READ_UNCOMMITTED")

        return self._engine

    def __init__(self, database, **options):
        super().__init__()

        self.update_interval = options.get('update_interval', 10)

        self._engine = None
        self._database = database
        self._conn = None
        self.last_start = datetime.datetime.now() - datetime.timedelta(seconds=self.update_interval)
        self._query = select([events.c.Id, monitors.c.Name, events.c.Cause, events.c.StartTime, events.c.Notes])\
            .select_from(events.join(monitors)) \
            .where(and_(events.c.StartTime > bindparam('last_start'), events.c.Cause == 'Motion'))

        self.loop = asyncio.get_event_loop()

        self._zones = {}

    def describe(self):
        return 'zoneminder.ZoneMinderSql/' + self._database

    async def fitness(self):
        def do_check():
            try:
                conn = self.engine.connect()

                monitor_names = set()
                result = conn.execute("SELECT `Name` from `Monitors`")
                for row in result:
                    monitor_names.add(row.Name)

                return monitor_names
            except:
                log.exception("Could not connect to ZoneMinder SQL database")
                return None
            finally:
                if conn:
                    conn.close()

        start = time.time()
        monitor_names = await self.loop.run_in_executor(None, do_check)
        dur = time.time() - start

        if monitor_names is not None:
            return -dur
        else:
            return 0

    def register_zone(self, monitor, zone, block):
        if monitor not in self._zones:
            self._zones[monitor] = {}

        self._zones[monitor][zone] = block

    def _connect_sync(self):
        self._conn = self.engine.connect()
        return self._conn

    def _new_events_sync(self):
        result = self._conn.execute(self._query, last_start=self.last_start)

        new_events = []
        for row in result:
            new_events.append({
                "id": row.Id,
                "monitor": row.Name,
                "cause": row.Cause,
                "start_time": row.StartTime,
                "notes": row.Notes,
                "zones": row.Notes[len('Motion: '):].split(', ') if row.Notes.startswith('Motion: ') else [],
            })


        return new_events

    async def connect(self):
        return await self.loop.run_in_executor(None, self._connect_sync)

    async def new_events(self):
        return await self.loop.run_in_executor(None, self._new_events_sync)

    async def update(self):
        new_events = await self.new_events()
        dispatch = []

        for event in new_events:
            if event["start_time"] > self.last_start:
                self.last_start = event["start_time"]

            if event["monitor"] in self._zones:
                for zone in event["zones"]:
                    if zone in self._zones[event["monitor"]]:
                        block = self._zones[event["monitor"]][zone]

                        dispatch.append(block._update(event["monitor"], zone))

        await asyncio.gather(*dispatch)

    async def ready(self):
        while not self._conn:
            await asyncio.sleep(1)

    async def run(self):
        if self.running:
            return

        self.running = True

        await self.connect()

        backoff = 0

        while True:
            try:
                await self.update()
                await asyncio.sleep(self.update_interval)
                backoff = 0
            except:
                log.exception("Exception updating zoneminder events...")
                log.debug("Trying again in %d seconds", 2 ** min(backoff, 9))
                await asyncio.sleep(2 ** min(backoff, 9))
                backoff += 1


class Zone(block.Block):
    def __init__(self, name, monitor=None, zone=None, **config):
        super().__init__(name, **config)

        base_settings = global_config.get('modules', {}).get('zoneminder', {})
        self.config.setdefault('database', base_settings.get('database', 'sqlite:///memory'))

        self.monitor = monitor
        self.zone = zone

        self.database = ZoneMinderSql.instance(self.config['database'])
        self.require(self.database)

    async def _update(self, monitor, zone):
        if self.monitor == '*' or self.zone == '*':
            if (self.monitor == '*' or self.monitor == monitor) \
                and (self.zone == '*' or self.zone == zone):

                await self.output(monitor, 'monitor')
                await self.output(zone, 'zone')

        await self.output(True)

    async def run(self, *_, **__):
        while not self.database:
            await asyncio.sleep(1)

        self.database.register_zone(self.monitor, self.zone, self)

        await self.database.ready()
        await super().run()
