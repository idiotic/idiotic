class MissingResource(Exception):
    pass


class Resource:
    def __init__(self):
        self.available = False

    def try_check(self):
        if not self.available:
            raise MissingResource(self)

    async def run(self):
        pass
