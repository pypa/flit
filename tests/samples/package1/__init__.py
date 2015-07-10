"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        __version__, 'package1', 'Sir Robin', 'robin@camelot.uk',
        'http://github.com/sirrobin/package1',
        scripts={ 'pkg-script': 'package1:main' },
        )

def main():
    print("package1 main")
