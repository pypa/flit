"""
This module contains the implementation of the "installfrom" subcommand.
"""

import sys

from ..installfrom import installfrom
from .install import add_shared_install_options

NAME = 'installfrom'
HELP = "Download and install a package using flit from source"


def setup(parser):
    parser.add_argument(
        'location',
        help="A URL to download, or a shorthand like github:takluyver/flit"
    )
    add_shared_install_options(parser)


def run(args):
    returncode = installfrom(args.location, user=args.user, python=args.python)
    return returncode
