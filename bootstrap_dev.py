"""Use this script to get set up for working on flit itself.

python bootstrap_dev.py

This symlinks flit into site-packages, and installs the flit command.
"""

from flit import Importable
from flit.install import Installer

i = Importable('flit')
i.check()
Installer(i, symlink=True).install()
