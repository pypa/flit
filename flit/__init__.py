"""A simple packaging tool for simple packages."""
import argparse
import logging
from pathlib import Path
import sys

from . import common
from .log import enable_colourful_output
from .subcmds import Subcommand, SubcommandArgumentParser

__version__ = '1.0'

log = logging.getLogger(__name__)

def add_ini_file_option(parser):
    default = pyproject = Path('pyproject.toml')
    flit_ini = Path('flit.ini')
    if flit_ini.is_file() and not pyproject.is_file():
        default = flit_ini
    parser.add_argument('-f', '--ini-file', type=Path, default=default,
        help=""
    )


subcmds = [
    Subcommand('build', func='flit.build:main', help="Build wheel and sdist"),
    Subcommand('publish', func='flit.upload:main', help="Upload wheel and sdist"),
    Subcommand('install', func='flit.install:main', help="Install the package"),
    Subcommand('installfrom', func='flit.installfrom:main',
               help="Download and install a package using flit from source"),
    Subcommand('init', func='flit.init:main',
               help="Prepare pyproject.toml for a new package")
]

def main(argv=None):
    ap = SubcommandArgumentParser()
    ap.add_argument('--version', action='version', version='Flit '+__version__)
    ap.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--logo', action='store_true', help=argparse.SUPPRESS)
    ap.add_subcommands(subcmds)

    args = ap.parse_args(argv)

    enable_colourful_output(logging.DEBUG if args.debug else logging.INFO)

    log.debug("Parsed arguments %r", args)

    if args.logo:
        from .logo import clogo
        print(clogo.format(version=__version__))
        sys.exit(0)

    ap.dispatch_subcommand(args)
