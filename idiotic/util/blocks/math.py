from operator import sub, mul, truediv, floordiv
from .logic import MultiInputBlock
from functools import reduce


class SumBlock(MultiInputBlock):
    def calculate(self, *args):
        return sum(args)


class AddBlock(SumBlock):
    pass


class AverageBlock(MultiInputBlock):
    def calculate(self, *args):
        return sum(args) / len(args)


class SubtractBlock(MultiInputBlock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._any_params:
            raise ValueError("Cannot use automatic parameters for this block; non-deterministic behavior would result")

    def calculate(self, *args):
        return reduce(sub, args)


class NegativeBlock(SubtractBlock):
    def calculate(self, *args):
        return super().calculate(0, *args)


class ProductBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(mul, args)


class MultiplyBlock(ProductBlock):
    pass


class DivideBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(truediv, args)


class IntDivideBlock(MultiInputBlock):
    def calculate(self, *args):
        return reduce(floordiv, args)
