from operator import sub, mul, truediv, floordiv
from .logic import MultiInputBlock
from functools import reduce


class Sum(MultiInputBlock):
    def calculate(self, *args):
        return sum(args)


class Add(Sum):
    pass


class Average(MultiInputBlock):
    def calculate(self, *args):
        return sum(args) / len(args)


class Subtract(MultiInputBlock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._any_params:
            raise ValueError("Cannot use automatic parameters for this block; non-deterministic behavior would result")

    def calculate(self, *args):
        return reduce(sub, args)


class Negative(Subtract):
    def calculate(self, *args):
        return super().calculate(0, *args)


class Product(MultiInputBlock):
    def calculate(self, *args):
        return reduce(mul, args)


class Multiply(Product):
    pass


class Divide(MultiInputBlock):
    def calculate(self, *args):
        return reduce(truediv, args)


class IntDivide(MultiInputBlock):
    def calculate(self, *args):
        return reduce(floordiv, args)
