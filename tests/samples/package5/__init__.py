"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        version=__version__,
        module='package5',
        author='Sir Robin',
        author_email='robin@camelot.uk',
        home_page='http://github.com/sirrobin/package5',
        scripts={ 'pkg_script': 'package5:main' },
        entry_points_file='console_entry_points.txt'
        )

def main():
    print("package5 main")
