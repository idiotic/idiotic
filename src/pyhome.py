#!/usr/bin/env python3
"""A python-based Home Automation Hub

Usage:
  pyhome.py --help
  pyhome.py --version
  pyhome.py [--base=<dir> | [--config=<file>] [--rules=<dir>] [--items=<dir>] [--ui=<dir>]] [-v | -vv] [-s]

Options:
  -h --help           Show this text.
     --version        Print the version
  -v --verbose        Set verbosity.
  -b --base=<dir>     Path to pyHome config base directory [default: /etc/pyhome].
  -c --config=<file>  Path to pyHome config file [default: /etc/pyhome/conf.json].
  -r --rules=<dir>    Path to rules config directory [default: /etc/pyhome/rules].
  -i --items=<dir>    Path to Item config directory [default: /etc/pyhome/items].
  -u --ui=<dir>       Path to UI config directory [defaul: /etc/pyhome/ui].
  -s --standalone     Run without connecting to other instances.
"""

import docopt

def main():
    # load command-line options
    arguments = docopt.docopt(__doc__, "Current version")
    print(arguments)
    # load configuration
    # load bindings
    # load items
    # load rules
    # load ui
    # read database
    # correspond with other instances?
    # start running updates / bindings
    # start running rules
    # start serving API
    # start serving UI

if __name__ == '__main__':
    main()
