"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        __version__, 'package4', 'Sir Robin', 'robin@camelot.uk',
        'http://github.com/sirrobin/package4',
        scripts={ 'pkg_script': 'package4:main' },
        entry_points_file='some_entry_points.txt'
        )

def main():
    print("package4 main")
