"""A simple packaging tool for simple packages."""
import argparse
import logging
import pathlib
import sys

from . import common
from .subcommand import register
from .log import enable_colourful_output

__version__ = '1.3'

log = logging.getLogger(__name__)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--ini-file', type=pathlib.Path, default='pyproject.toml')
    ap.add_argument('-V', '--version', action='version', version='Flit '+__version__)
    ap.add_argument('--repository',
        help="Name of the repository to upload to (must be in ~/.pypirc)"
    )
    ap.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--logo', action='store_true', help=argparse.SUPPRESS)

    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')
    register(subparsers, 'build')
    register(subparsers, 'publish')
    register(subparsers, 'install')
    register(subparsers, 'installfrom')
    register(subparsers, 'info')

    args = ap.parse_args(argv)

    cf = args.ini_file
    if (
        args.subcmd not in {'init', 'installfrom'}
        and cf == pathlib.Path('pyproject.toml')
        and not cf.is_file()
    ):
        # Fallback to flit.ini if it's present
        cf_ini = pathlib.Path('flit.ini')
        if cf_ini.is_file():
            args.ini_file = cf_ini
        else:
            sys.exit('Neither pyproject.toml nor flit.ini found, '
                     'and no other config file path specified')

    enable_colourful_output(logging.DEBUG if args.debug else logging.INFO)

    log.debug("Parsed arguments %r", args)

    if args.logo:
        from .logo import clogo
        print(clogo.format(version=__version__))
        sys.exit(0)

    if args.subcmd:
        exitcode = args.subcmd_entrypoint(args)
        sys.exit(exitcode)
    else:
        ap.print_help()
        sys.exit(1)
