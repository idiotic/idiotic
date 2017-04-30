from idiotic import block
from collections import OrderedDict
from operator import eq, ne, gt, lt, ge, le
from functools import reduce


class MultiInputBlock(block.Block):
    def __init__(self, *args, parameters=None, default=None, initial=None, **kwargs):
        super().__init__(*args, **kwargs)

        if parameters:
            self._any_params = False
            self._param_dict = OrderedDict(( (k, default) for k in parameters))
        else:
            self._any_params = True
            self._param_dict = OrderedDict()

        self._value = initial

    def __getattr__(self, key):
        if self._any_params or key in self._param_dict:
            async def __input(val):
                self._param_dict[key] = val
                await self._recalculate()
            return __input
        else:
            raise ValueError("Parameter name not declared")

    async def _recalculate(self):
        value = self.calculate(*self._param_dict.values())

        if value != self._value:
            self._value = value
            await self.output(self._value)


class OrBlock(MultiInputBlock):
    def calculate(self, *args):
        return any(args)


class AndBlock(MultiInputBlock):
    def calculate(self, *args):
        return all(args)


class NotBlock(MultiInputBlock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if len(self._param_dict) > 1:
            raise ValueError("Must have exactly one parameter")

    def calculate(self, arg, *extra):
        if extra:
            raise ValueError("Must only have one argument")

        return not arg


class NotEqualBlock(MultiInputBlock):
    def calculate(self, *args):
        # No duplicates == nothing is equal to anything else
        # If I just chained != operator, [1, 2, 1] would return True
        return len(set(args)) == len(args)


class EqualBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(eq, args)


class GreaterThanBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(gt, args)


class GreaterThanEqualBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(ge, args)


class LessThanBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(lt, args)


class LessThanEqualBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(le, args)


class OutputIfBlock(block.Block):
    def __init__(self, *args, initial=None, output_condition=True, output_value=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._condition = False
        self._value = initial

        self.output_condition = output_condition
        self.output_value = output_value

    async def condition(self, cond):
        if not self._condition and cond and self.output_condition:
            await self.output(self._value)
        self._condition = cond

    async def value(self, val):
        self._value = val

        if self._condition and self.output_value:
            await self.output(self._value)


class TernaryBlock(block.Block):
    def __init__(self, *args, initial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._condition = False
        self._true = initial
        self._false = initial

    async def condition(self, cond):
        if self._condition == cond:
            return

        self._condition = cond

        if self._condition:
            await self.output(self._true)
        else:
            await self.output(self._false)

    async def true(self, val):
        self._true = val

        if self._condition:
            await self.output(self._true)

    async def false(self, val):
        self._false = val

        if not self._condition:
            await self.output(self._false)