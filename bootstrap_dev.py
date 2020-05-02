#!/usr/bin/env python3

# Symlink install flit & flit_core for development.
# Most projects can do the same with 'flit install --symlink'.
# But that doesn't work until Flit is installed, so we need some bootstrapping.

import argparse
import logging
import os
from pathlib import Path
import sys

my_dir = Path(__file__).parent
os.chdir(str(my_dir))
sys.path.insert(0, 'flit_core')

from flit_core import build_thyself
from flit_core.config import LoadedConfig
from flit.install import Installer

ap = argparse.ArgumentParser()
ap.add_argument('--user')
args = ap.parse_args()

logging.basicConfig(level=logging.INFO)

# Construct config for flit_core
core_config = LoadedConfig()
core_config.module = 'flit_core'
core_config.metadata = build_thyself.metadata_dict
core_config.reqs_by_extra['.none'] = build_thyself.metadata.requires_dist

install_kwargs = {'symlink': True}
if os.name == 'nt':
    # Use .pth files instead of symlinking on Windows
    install_kwargs = {'symlink': False, 'pth': True}

# Install flit_core
Installer(
    my_dir / 'flit_core', core_config, user=args.user, **install_kwargs
).install()
print("Linked flit_core into site-packages.")

# Install flit
Installer.from_ini_path(
    my_dir / 'pyproject.toml', user=args.user, **install_kwargs
).install()
print("Linked flit into site-packages.")
