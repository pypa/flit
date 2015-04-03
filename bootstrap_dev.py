"""Use this script to get set up for working on flit itself.

python bootstrap_dev.py

This symlinks flit into site-packages, and installs the flit command.
"""

from pathlib import Path
from flit.install import Installer
from flit.log import enable_colourful_output

enable_colourful_output()
p = Path('flit.ini')
Installer(p, symlink=True).install()
