import os
import sys
import configparser
config = configparser.ConfigParser()
config.read('setup.cfg')
deps = [x for x in config['rpm_builder']['python_requires'].split("\n") if x]
for i in deps:
    print("Attempting to build {}".format(i))
    if os.system('CC="cc -mavx2" fpm --python-bin /usr/bin/python3 -s python -t rpm --verbose --python-package-name-prefix python3 {}'.format(i)):
        print("Failed to build {}!".format(i))
        sys.exit(-1)
