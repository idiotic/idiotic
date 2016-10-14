import logging

from idiotic import block
from idiotic import resource
from idiotic import config
import subprocess
import asyncio

import types


class Speech(block.Block):
    def __init__(self, name, text=None, parameters=None, defaults=None, command=None):
        self.name = name

        self.speech_command = command or config.config.get("modules", {}).get("espeak", {}).get("command", "espeak")

        self._text = text
        self.parameters = parameters or []

        self.data = {}
        self.defaults = defaults or {}

        self._param_dict = {n: self.defaults.get(n, None) for n in self.parameters}

        for name in self.parameters:
            async def setparam(self, val):
                await self._setparam(name, val)

            setattr(self, name, types.MethodType(setparam, self))

        self.inputs = {}
        self.resources = []

    async def _setparam(self, name, value):
        self._param_dict[name] = value
        await self.speak()

    async def text(self, text):
        self._text = text
        await self.speak()

    def _speak(self):
        try:
            logging.debug("Saying \"{}\"".format(self._text.format(**self._param_dict)))
            subprocess.run("espeak --stdout | paplay", input=self._text.format(**self._param_dict).encode('UTF-8'), shell=True)
        except subprocess.CalledProcessError as e:
            logging.error("While trying espeak...")

    async def speak(self, *_):
        await asyncio.get_event_loop().run_in_executor(None, self._speak)
