"""
Docstring formatted like this.
"""

from flit.inifile import flit_config

__version__ = '7.0'
__FLIT__ = flit_config(
        __version__, 'module2', 'Sir Robin', 'robin@camelot.uk',
        'http://github.com/sirrobin/module3'
        )
