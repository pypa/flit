"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        __version__, 'package2', 'Sir Robin', 'robin@camelot.uk',
        'http://github.com/sirrobin/package2',
        scripts={ 'pkg-script': 'package2:main' },
        entry_points_file='nonexistant_entry_points.txt'
        )

def main():
    print("package1 main")
