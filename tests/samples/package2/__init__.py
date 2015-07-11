"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        version=__version__,
        module='package2',
        author='Sir Robin',
        author_email='robin@camelot.uk',
        home_page='http://github.com/sirrobin/package2',
        scripts={ 'pkg_script': 'package2:main' },
        entry_points_file='nonexistant_entry_points.txt'
        )

def main():
    print("package2 main")
