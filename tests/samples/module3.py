"""Example module"""

from flit.inifile import flit_config

__version__ = '0.1'
__FLIT__ = flit_config(
        version=__version__,
        module='module3',
        author='Sir Robin',
        author_email='robin@camelot.uk',
        home_page='http://github.com/sirrobin/module3',
        classifiers='License :: OSI Approved :: BSD License  Intended Audience :: Pacman'
        )
