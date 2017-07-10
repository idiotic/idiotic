from setuptools import setup, find_packages

def read_license():
    with open("LICENSE") as f:
        return f.read()

setup(
    name='idiotic',
    packages=find_packages(exclude=['etc', 'contrib']),
    version='2.0.0',
    description='Distributed home automation controller',
    long_description="""The idiotic distributed internet of things inhabitance
    controller (idiotic), aims to be an extremely extensible, capable, and most
    importantly developer-and-user-friendly solution for mashing together a wide
    assortment of existing home automation technologies into something which is
    useful as a whole.""",    
    license=read_license(),
    author='Dylan Whichard',
    author_email='dylan@whichard.com',
    url='https://github.com/umbc-hackafe/idiotic',
    keywords=[
        'home automation', 'iot', 'internet of things'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Home Automation',
    ],
    install_requires=[
        'pysyncobj>=0.2.1',
        'PyYAML',
        'aiohttp',
        'flask',
    ],
    data_files=[
        ('/usr/lib/systemd/system/', ['contrib/idiotic.service']),
        ('/etc/idiotic/', ['contrib/conf.yaml']),
    ],
    entry_points={
        'console_scripts': [
            'idiotic=idiotic.__main__:main',
        ]
    },
)
