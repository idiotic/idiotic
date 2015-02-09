import os
import sys
import imp
import logging

def load_dir(path):
    sys.path.insert(0, os.path.abspath("."))
    files = []
    for _, _, f in os.walk(path):
        files.extend(f)
        break

    modules = []
    for f in files:
        try:
            if f.endswith("~") or f.endswith("#"):
                continue
            logging.info("Loading file {}...".format(os.path.join(path, f)))
            name = os.path.splitext(f)[0]
            modules.append(imp.load_source(name, os.path.join(path, f)))
        except Exception as e:
            logging.exception("Exception encountered while loading {}".format(os.path.join(path, f)))
    return modules
