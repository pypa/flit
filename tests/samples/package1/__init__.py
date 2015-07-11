"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        version=__version__,
        module='package1',
        author='Sir Robin',
        author_email='robin@camelot.uk',
        home_page='http://github.com/sirrobin/package1',
        scripts={ 'pkg_script': 'package1:main' },
        )

def main():
    print("package1 main")
