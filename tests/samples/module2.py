"""
Docstring formatted like this.
"""

from flit.inifile import flit_config

__version__ = '7.0'
__FLIT__ = flit_config(
        version=__version__,
        module='module2',
        author='Sir Robin',
        author_email='robin@camelot.uk',
        home_page='http://github.com/sirrobin/module3'
        )
