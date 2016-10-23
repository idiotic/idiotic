from idiotic import block
import functools
import asyncio


class RPiGPIO(block.Block, block.ParameterBlock):
    def __init__(self, *args, device=None, options=None, **kwargs):
        super().__init__(*args, **kwargs)

        if device is None:
            raise ValueError("Device is not given")

        self.device_type = device
        self.device_args = options or {}
        self.device = None

    async def run_events(self):
        loop = asyncio.get_event_loop()
        if self.device.is_active:
            await loop.run_in_executor(None, self.device.wait_for_inactive)
            print("############ GPIO Device Active (" + self.name + ")")
            await self.output(self.device.value)
        else:
            await loop.run_in_executor(None, self.device.wait_for_active)
            await self.output(self.device.value)
            print("############ GPIO Device Inactive (" + self.name + ")")

    async def parameter_changed(self, key, value):
        await asyncio.get_event_loop().run_in_executor(None, functools.partial(getattr(self.device, key), **value))

    async def run(self, *_, **__):
        import gpiozero

        device_cls = getattr(gpiozero, self.device_type)
        self.device = device_cls(**self.device_args)

        while True:
            if isinstance(self.device, gpiozero.EventsMixin):
                await self.run_events()
            else:
                raise ValueError("I don't know what to do with this!")