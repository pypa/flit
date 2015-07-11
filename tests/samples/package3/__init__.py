"""A sample package"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        version=__version__,
        module='package3',
        author='Sir Robin',
        author_email='robin@camelot.uk',
        home_page='http://github.com/sirrobin/package3',
        scripts={ 'pkg_script': 'package3:main' },
        dist_name='packagedist1'
        )

def main():
    print("package3 main")
