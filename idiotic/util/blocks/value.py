from idiotic import block
import json


class Value(block.Block):
    def __init__(self, name, kind="str", initial=None):
        super().__init__(name)

        self.kind = kind

        self._value = initial

    def coerce(self, val):
        if self.kind == "int":
            return int(val)
        elif self.kind == "str":
            return str(val)
        elif self.kind == "float":
            return float(val)
        elif self.kind == "bool":
            return bool(val)
        elif self.kind == "json":
            return json.loads(val)
        else:
            raise ValueError("Invalid kind {}".format(self.kind))

    async def value(self, val):
        self._value = self.coerce(val)
        await self.output(self._value)

    async def run(self, *args, **kwargs):
        if self._value is not None:
            await self.output(self._value)

        await super().run()


class Int(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="int", **kwargs)


class Str(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="str", **kwargs)


class Float(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="float", **kwargs)


class Bool(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="bool", **kwargs)


class JSON(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="json", **kwargs)
