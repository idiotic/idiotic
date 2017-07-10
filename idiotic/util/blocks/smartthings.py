import requests
from idiotic import block
from idiotic import resource
from idiotic import node
from idiotic.config import config as global_config
from idiotic.util.resources import http
import asyncio
import aiohttp
import logging

log = logging.getLogger(__name__)


class Location:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class SmartApp(resource.Resource):
    APPS = {}

    @classmethod
    def instance(cls, token, endpoints_uri, location_name):
        if token not in cls.APPS:
            res = cls(token, endpoints_uri, location_name)
            cls.APPS[res.describe()] = res
            return res

        return cls.APPS['smartthings.SmartApp/' + token + '/' + location_name]

    def __init__(self, token, endpoints_uri, location_name):
        super().__init__()

        self.token = token
        self.endpoints_uri = endpoints_uri
        self.location_name = location_name

        self.headers = {'Authorization': 'Bearer ' + self.token}

        # URI is the full address of our SmartApp installation
        self.uri = None

        # Base URL is the regional server we connect to
        self.base_url = None

        # URL is just the path of our SmartApp installation
        self.url = None
        self.location = None

        self._client = aiohttp.ClientSession()

    def describe(self):
        return 'smartthings.SmartApp/' + self.token + '/' + self.location_name

    async def ready(self):
        while not self.location:
            await asyncio.sleep(1)

    async def command(self, device_id, name, *args, subpath='devices', **options):
        async with self._client.put('/'.join((self.uri, subpath, device_id, name)),
                                    headers=self.headers,
                                    json={'args':args,'options':options}) as response:
            response.raise_for_status()

    async def switches(self):
        await self.ready()

        async with self._client.get(self.uri + '/switches', headers=self.headers) as response:
            response.raise_for_status()
            switches = await response.json()
            return switches

    async def fitness(self):
        try:
            async with self._client.get(self.endpoints_uri, headers=self.headers) as response:
                response.raise_for_status()
                locations = await response.json()

                for loc in locations:
                    if loc['location']['name'] == self.location_name:
                        self.uri = loc['uri']
                        self.base_url = loc['base_url']
                        self.url = loc['url']
                        self.location = Location(loc['location']['id'], loc['location']['name'])
                        return True

                log.error("Unable to find SmartThings location '%s'", self.location_name)
                return False
        except:
            log.exception("Could not reach SmartThings API")
            return False

    async def run(self):
        await super().run()
        await self.ready()


class Device(block.Block):
    def __init__(self, name, id=None, label=None, **config):
        super().__init__(name, **config)
        base_settings = global_config.get("modules", {}).get("smartthings", {})
        self.config.setdefault('client_id', base_settings.get('client_id', '42195b52-83f9-4012-b804-db39120bf7a4'))
        self.config.setdefault('endpoints_uri', base_settings.get('endpoints_uri',
                                                                  'https://graph.api.smartthings.com/api/smartapps/endpoints'))
        self.config.setdefault('oauth_token', base_settings.get('oauth_token', None))
        self.config.setdefault('location', base_settings.get('location', None))
        self.oauth_token = self.config['oauth_token']

        self.id = id
        self.label = label
        self.display = None

        self.status = 'UNKNOWN'

        if not self.oauth_token:
            raise ValueError("OAuth token not provided")

        self.smartapp = SmartApp.instance(self.config['oauth_token'], self.config['endpoints_uri'], self.config['location'])

        self.require(http.HostReachable(self.config.get('endpoints_uri')), self.smartapp)

    async def _update(self, data):
        if 'status' in data:
            await self._status(data['status'])
        if 'display' in data:
            self.display = data['display']
        if 'label' in data and not self.label:
            self.label = data['label']
        if 'id' in data and not self.id:
            self.id = data['id']

    async def _status(self, val):
        self.status = val
        await self.output(val, 'status')

    async def command(self, name, *args, **options):
        await self.smartapp.command(self.id, name, *args, **options)

    async def run(self, *_, **__):
        while not self.smartapp:
            await asyncio.sleep(1)

        await self.smartapp.ready()


class Switch(Device):
    def __init__(self, name, **config):
        super().__init__(name, **config)
        self.power_state = None

        self.device = None

    async def command(self, *args, **kwargs):
        await super().command(*args, subpath='switches', **kwargs)

    async def on(self):
        await self.command('on')

    async def off(self):
        await self.command('off')

    async def power(self, value):
        if value:
            await self.on()
        else:
            await self.off()

    async def _update(self, data):
        await super()._update(data)

    async def run(self):
        await super().run()

        for dev in await self.smartapp.switches():
            if dev['id'] == self.id or dev['label'] == self.label:
                await self._update(dev)
                break
        else:
            raise NameError("Could not find SmartThings device '{}'".format(self.id or self.label))

        while True:
            await asyncio.sleep(3600)


class Dimmer(Device):
    def __init__(self, name, **config):
        super().__init__(name, **config)
        self.brightness = None

    async def brightness(self, value):
        self.brightness = value

        await asyncio.get_event_loop().run_in_executor(None, self.device.set_brightness, value)
