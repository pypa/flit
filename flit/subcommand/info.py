"""
This module contains the implementation for the "info" subcommand
"""

import sys

from .. import inifile
from ..common import Module, make_metadata

NAME = 'info'
HELP = "Retrieve metadata information from the project"


def setup(parser):
    parser.add_argument(
        '--version', default=False, action='store_true', dest='show_version',
        help="Print the version number of the project to stdout"
    )


def run(args):
    ini_info = inifile.read_pkg_ini(args.ini_file)
    module = Module(ini_info['module'], args.ini_file.parent)
    metadata = make_metadata(module, ini_info)
    output = metadata.version
    print(output)
    return 0
