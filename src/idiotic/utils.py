import collections
import datetime
import logging
import bisect
import imp
import sys
import os

class History:
    def __init__(self, initial=[], maxlen=None, maxage=None):
        self.values = collections.deque(sorted(initial), maxlen=maxlen)

        if isinstance(maxage, int):
            self.maxage = datetime.timedelta(seconds=maxage)
        elif isinstance(maxage, datetime.timedelta):
            self.maxage = maxage
        elif maxage is None:
            self.maxage = None
        else:
            raise ValueError("maxage must be int or timedelta")

    def cull(self):
        if self.maxage:
            pos = bisect.bisect_left(list(zip(*self.values))[0], datetime.datetime.now() - self.maxage)
            for i in range(pos):
                self.value.popleft()

    def record(self, value, time=None):
        if time is None:
            self.values.append((datetime.datetime.now(), value))
        elif isinstance(time, datetime.datetime):
            if time < self.values[-1][0]:
                raise NotImplementedError("We can't alter history!... yet....")
            else:
                self.values.append((time, value))
        else:
            raise ValueError("time must be datetime")

    def at(self, time):
        return self.values[bisect.bisect(list(zip(*self.values))[0], time)-1]

    def all(self):
        return list(self.values)

    def last(self, nth=1):
        return self.values[-nth]

    def __getitem__(self, pos):
        return list(self.values)[pos]

    def __str__(self):
        return str(self.values)

def load_dir(path, include_assets=False):
    sys.path.insert(0, os.path.abspath("."))
    modules = []
    for f in os.listdir(path):
        try:
            if f.startswith(".") or f.endswith("~") or f.endswith("#") or f.startswith("__"):
                continue

            logging.info("Loading file {}...".format(os.path.join(path, f)))
            name = os.path.splitext(f)[0]

            try:
                modules.append((imp.load_source(name, os.path.join(path, f)), None))
            except IsADirectoryError:
                logging.info("Attempting to load directory {} as a module...".format(
                    os.path.join(path, f)))

                try:
                    mod = imp.load_source(name, os.path.join(path, f, '__init__.py'))
                    assets = None
                    if os.path.exists(os.path.join(path, f, 'assets')) and \
                       os.path.isdir(os.path.join(path, f, 'assets')):
                        assets = os.path.abspath(os.path.join(path, f, 'assets'))

                    modules.append((mod, assets))
                except FileNotFoundError:
                    logging.error("Unable to load module {}: {} does not exist".format(
                        name, os.path.join(path, f, '__init__.py')))
        except Exception as e:
            logging.exception("Exception encountered while loading {}".format(os.path.join(path, f)))

    return modules
