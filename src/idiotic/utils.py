import os
import sys
import imp
import logging

def load_dir(path):
    sys.path.insert(0, os.path.abspath("."))
    modules = []
    for f in os.listdir(path):
        try:
            if f.startswith(".") or f.endswith("~") or f.endswith("#") or f.startswith("__"):
                continue

            logging.info("Loading file {}...".format(os.path.join(path, f)))
            name = os.path.splitext(f)[0]

            try:
                modules.append(imp.load_source(name, os.path.join(path, f)))
            except IsADirectoryError:
                logging.info("Attempting to load directory {} as a module...".format(
                    os.path.join(path, f)))

                try:
                    modules.append(imp.load_source(name, os.path.join(path, f, '__init__.py')))
                except FileNotFoundError:
                    logging.error("Unable to load module {}: {} does not exist".format(
                        name, os.path.join(path, f, '__init__.py')))
        except Exception as e:
            logging.exception("Exception encountered while loading {}".format(os.path.join(path, f)))

    return modules
