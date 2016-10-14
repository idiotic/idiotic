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
        print("{} set value to {}".format(self.name, self._value))
        await self.output(self._value)


class IntValue(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="int", **kwargs)


class StrValue(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="str", **kwargs)


class FloatValue(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="float", **kwargs)


class BoolValue(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="bool", **kwargs)


class JSONValue(Value):
    def __init__(self, name, **kwargs):
        super().__init__(name, kind="json", **kwargs)
