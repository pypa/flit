"""A simple packaging tool for simple packages."""
import argparse
import logging
import pathlib
import sys

from . import common
from . import inifile
from .log import enable_colourful_output

__version__ = '0.4'

log = logging.getLogger(__name__)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--ini-file', type=pathlib.Path, default='flit.ini')
    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')

    parser_wheel = subparsers.add_parser('wheel')
    parser_wheel.add_argument('--upload', action='store', nargs='?',
                              const='pypi', default=None,
          help="Upload the built wheel to PyPI"
    )
    parser_wheel.add_argument('--verify-metadata', action='store', nargs='?',
                              const='pypi', default=None,
          help="Verify the package metadata with the PyPI server"
    )

    parser_install = subparsers.add_parser('install')
    parser_install.add_argument('--symlink', action='store_true',
        help="Symlink the module/package into site packages instead of copying it"
    )
    parser_install.add_argument('--user', action='store_true', default=None,
        help="Do a user-local install (default if site.ENABLE_USER_SITE is True)"
    )
    parser_install.add_argument('--env', action='store_false', dest='user',
        help="Install into sys.prefix (default if site.ENABLE_USER_SITE is False, i.e. in virtualenvs)"
    )

    args = ap.parse_args(argv)

    enable_colourful_output()

    if args.subcmd == 'wheel':
        from .wheel import WheelBuilder
        WheelBuilder(args.ini_file, upload=args.upload,
                     verify_metadata=args.verify_metadata).build()
    elif args.subcmd == 'install':
        from .install import Installer
        Installer(args.ini_file, user=args.user, symlink=args.symlink).install()
    else:
        sys.exit('No command specified')

if __name__ == '__main__':
    main()