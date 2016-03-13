from setuptools import setup, find_packages

setup(
    name='idiotic',
    packages=find_packages(exclude=['etc', 'contrib']),
    version='0.1.0',
    description='Distributed home automation controller',
    long_description="""The idiotic distributed internet of things inhabitance
    controller (idiotic), aims to be an extremely extensible, capable, and most
    importantly developer-and-user-friendly solution for mashing together a wide
    assortment of existing home automation technologies into something which is
    useful as a whole.""",    
    license="""The MIT License (MIT)

    Copyright (c) 2015-2016 Hackafe and contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
""",
    author='Dylan Whichard',
    author_email='dylan@whichard.com',
    url='https://github.com/umbc-hackafe/idiotic',
    keywords=[
        'home automation', 'iot', 'internet of things'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Framework :: Flask',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Home Automation',
    ],
    install_requires=[
        'docopt>=0.6.2',
        'schedule>=0.3.2',
        'asyncio',
        'aiohttp>=0.21.2',
        'werkzeug0.11.4',
        'Flask>=0.10.1',
        'Flask-aiohttp>=0.1.0',
    ],
    data_files=[
        ('/usr/lib/systemd/system/idiotic.service', ['contrib/idiotic.service']),
        ('/etc/idiotic/', ['contrib/conf.json']),
    ],
    entry_points={
        'console_scripts': [
            'idiotic=idiotic.__main__:main',
        ]
    },
)
