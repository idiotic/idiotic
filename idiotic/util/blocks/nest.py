import requests
from idiotic import block
from idiotic.config import config as global_config
from idiotic.util.resources import module
from idiotic import resource
from idiotic import node
import functools
import itertools
import asyncio
import aiohttp
import logging
import nest
import time
import copy

PRODUCT_ID = 'f5b06fb6-9152-4de5-b123-4fc640b4fbd6'

log = logging.getLogger(__name__)


def _float_same(a, b, decimals=3):
    # If either of these isn't a float, don't worry about it
    if not (isinstance(a, float) and isinstance(b, float)):
        return False
    return abs(a - b) < 10 ** (-decimals)


class DeviceNotFound(Exception):
    pass


class NestApi(resource.Resource):
    APPS = {}

    @classmethod
    def instance(cls, token, **options):
        if token not in cls.APPS:
            res = cls(token, **options)
            cls.APPS[res.describe()] = res
            return res

        return cls.APPS['nest.NestApi/' + token]

    def __init__(self, token, **options):
        super().__init__()

        cache_ttl = options.get('update_interval', 60)
        if cache_ttl < 60:
            if not options.get('promise_to_be_good', False):
                cache_ttl = 60
                log.warn("Update interval set too low. Setting back up to 1 "
                         "minute unless you set promise_to_be_good: yes")

        self.token = token
        self.loop = asyncio.get_event_loop()
        self.napi = nest.Nest(client_id=PRODUCT_ID,
                              access_token=token,
                              cache_ttl=cache_ttl)

        self._devices = {}
        self._update_internal = cache_ttl

    def describe(self):
        return 'nest.NestApi/' + self.token

    async def fitness(self):
        try:
            start = time.time()
            structures = await self.loop.run_in_executor(None, lambda: self.napi.structures)
            dur = time.time() - start
            if structures:
                return -dur
            else:
                return 0
        except:
            log.exception("Could not reach nest API")
            return 0

    async def structures(self):
        return await self.loop.run_in_executor(None, lambda: self.napi.structures)

    async def thermostats(self):
        return await self.loop.run_in_executor(None, lambda: self.napi.thermostats)

    async def cameras(self):
        return await self.loop.run_in_executor(None, lambda: self.napi.cameras)

    async def alarms(self):
        return await self.loop.run_in_executor(None, lambda: self.napi.smoke_co_alarms)

    async def update(self):
        for device in itertools.chain(await self.structures(),
                                      await self.thermostats(),
                                      await self.cameras(),
                                      await self.alarms()):
            if device.serial in self._devices:
                await self._devices[device.serial].update(device)

    async def find_device(self, serial=None, name=None, type=None):
        search_devices = []

        if serial:
            search_devices = itertools.chain(
                await self.structures(),
                await self.thermostats(),
                await self.cameras(),
                await self.alarms()
            )
        elif name and type:
            if type.lower() == 'thermostat':
                search_devices = await self.thermostats()
            elif type.lower() == 'camera':
                search_devices = await self.cameras()
            elif type.lower() == 'structure':
                search_devices = await self.structures()
            elif type.lower() in {'alarm', 'smoke_co_alarm', 'smoke_alarm', 'co_alarm'}:
                search_devices = await self.alarms()
            else:
                raise ValueError("Invalid device type: " + type)
        else:
            raise ValueError("Must specify either serial or both name and type")

        for device in search_devices:
            if serial and device.serial == serial \
                    or name and name in (device.name, device.name_long):
                return device

        if serial:
            raise DeviceNotFound(serial)
        else:
            raise DeviceNotFound("{} '{}'".format(type, name))

    def add_device(self, serial, device):
        self._devices[serial] = device

    async def run(self):
        if self.running:
            return

        self.running = True

        backoff = 0

        while True:
            try:
                await self.update()
                await asyncio.sleep(self._update_internal)
                backoff = 0
            except:
                log.exception("Exception updating nest devices...")
                log.debug("Trying again in %d seconds", 2 ** min(backoff, 9))
                await asyncio.sleep(2 ** min(backoff, 9))
                backoff += 1


class Device(block.Block):
    @classmethod
    def props(cls):
        return ('serial', 'name', 'name_long', 'device_id', 'online',
                'description', 'is_thermostat', 'is_camera', 'is_smoke_co_alarm')

    def __init__(self, name, serial=None, label=None, kind=None, **config):
        super().__init__(name, **config)
        base_settings = global_config.get("modules", {}).get("nest", {})
        self.config.setdefault('client_id', base_settings.get('client_id', 'f5b06fb6-9152-4de5-b123-4fc640b4fbd6'))
        self.config.setdefault('oauth_token', base_settings.get('oauth_token', None))
        self.oauth_token = self.config['oauth_token']

        self.serial = serial
        self.label = label
        self.kind = kind

        if not self.oauth_token:
            raise ValueError("OAuth token not provided")

        self.client = NestApi.instance(self.config['oauth_token'], **base_settings)

        self.require(self.client, module.Module('nest'))

        self.loop = asyncio.get_event_loop()

        self._last = None
        self._device = None

    async def update(self, obj):
        if self._last:
            last = self._last
            self._last = {}
            for prop in self.props():
                prop_val = getattr(obj, prop)
                # Check that the values are different, and it isn't just
                # floating point rounding errors
                if last.get(prop) != prop_val \
                        and not _float_same(last.get(prop), prop_val, 2):
                    self._last[prop] = prop_val
                    await self.output(prop_val, prop)
        else:
            self._last = {}
            self._device = obj
            for prop in self.props():
                self._last[prop] = getattr(obj, prop)
                await self.output(getattr(obj, prop), prop)

    def _set_prop_sync(self, name, val):
        setattr(self._device, name, val)

    async def _set_prop(self, name, val):
        await self.loop.run_in_executor(None, functools.partial(self._set_prop_sync, name, val))
        await self.output(val, name)

    async def name(self, val):
        await self._set_prop('name', val)

    async def run(self, *args, **kwargs):
        if not self._device:
            self._device = await self.client.find_device(
                serial=self.serial,
                name=self.label,
                type=self.kind)

            self.serial = self._device.serial
            self.label = self._device.name

            self.client.add_device(self._device.serial, self)

            await self.update(self._device)

        await super().run(*args, **kwargs)


class Thermostat(Device):
    @classmethod
    def props(cls):
        return super().props() +\
               ('fan', 'humidity', 'mode', 'has_leaf', 'is_using_emergency_heat',
                'label', 'last_connection', 'postal_code', 'temperature_scale', 'is_locked',
                'locked_temperature', 'temperature', 'min_temperature', 'max_temperature',
                'target', 'eco_temperature', 'can_heat', 'can_cool', 'has_humidifier',
                'has_dehumidifier', 'has_fan', 'has_hot_water_control', 'hot_water_temperature',
                'hvac_state')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def fan(self, val):
        await self._set_prop('fan', val)

    async def mode(self, val):
        await self._set_prop('mode', val)

    async def temperature(self, val):
        await self._set_prop('temperature', val)

    async def target(self, val):
        await self._set_prop('target', val)

    async def eco_temperature(self, val):
        await self._set_prop('eco_temperature', val)
