from idiotic import block
from idiotic import config
import subprocess
import asyncio
import logging

log = logging.getLogger(__name__)


class Speech(block.Block):
    def __init__(self, name, text=None, parameters=None, defaults=None, command=None):
        self.name = name

        self.speech_command = command or config.config.get("modules", {}).get("espeak", {}).get("command", "espeak")

        self._text = text
        self.parameters = parameters or []

        self.data = {}
        self.defaults = defaults or {}

        self._param_dict = {n: self.defaults.get(n, None) for n in self.parameters}

        self.inputs = {}
        self.resources = []

    def __getattr__(self, key):
        if key in self._param_dict:
            async def __input(val):
                await self._setparam(key, val)
            return __input
        else:
            raise ValueError("Parameter name not declared")

    async def _setparam(self, name, value):
        self._param_dict[name] = value
        await self.speak()

    async def text(self, text):
        self._text = text
        await self.speak()

    def _speak(self):
        try:
            log.debug("Saying \"%s\"", self._text.format(**self._param_dict))
            subprocess.run(self.speech_command, input=self._text.format(**self._param_dict).encode('UTF-8'), shell=True)
        except subprocess.CalledProcessError as e:
            log.error("While trying espeak...")

    async def speak(self, *_):
        await asyncio.get_event_loop().run_in_executor(None, self._speak)
