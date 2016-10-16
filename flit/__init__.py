"""A simple packaging tool for simple packages."""
import argparse
import logging
import pathlib
import sys

from . import common
from .log import enable_colourful_output

__version__ = '0.10'

log = logging.getLogger(__name__)

def add_shared_install_options(parser):
    parser.add_argument('--user', action='store_true', default=None,
        help="Do a user-local install (default if site.ENABLE_USER_SITE is True)"
    )
    parser.add_argument('--env', action='store_false', dest='user',
        help="Install into sys.prefix (default if site.ENABLE_USER_SITE is False, i.e. in virtualenvs)"
    )
    parser.add_argument('--python', default=sys.executable,
        help="Target Python executable, if different from the one running flit"
    )

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--ini-file', type=pathlib.Path, default='flit.ini')
    ap.add_argument('--version', action='version', version='Flit '+__version__)
    ap.add_argument('--repository', default='pypi',
        help="Name of the repository to upload to (must be in ~/.pypirc)"
    )
    ap.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--logo', action='store_true', help=argparse.SUPPRESS)
    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')

    parser_wheel = subparsers.add_parser('wheel',
        help="Build a wheel package",
    )
    parser_wheel.add_argument('--upload', action='store_true',
          help="Upload the built wheel to PyPI"
    )
    parser_wheel.add_argument('--verify-metadata', action='store_true',
          help="Verify the package metadata with the PyPI server"
    )

    parser_install = subparsers.add_parser('install',
        help="Install the package",
    )
    parser_install.add_argument('-s', '--symlink', action='store_true',
        help="Symlink the module/package into site packages instead of copying it"
    )
    add_shared_install_options(parser_install)
    parser_install.add_argument('--deps', choices=['all', 'production', 'develop', 'none'], default='all',
        help="Which set of dependencies to install")

    parser_installfrom = subparsers.add_parser('installfrom',
       help="Download and install a package using flit from source"
    )
    parser_installfrom.add_argument('location',
        help="A URL to download, or a shorthand like github:takluyver/flit"
    )
    add_shared_install_options(parser_installfrom)

    parser_init = subparsers.add_parser('init',
        help="Prepare flit.ini for a new package"
    )

    subparsers.add_parser('register',
        help="register a package on PyPI without uploading any files"
    )

    args = ap.parse_args(argv)

    enable_colourful_output(logging.DEBUG if args.debug else logging.INFO)

    log.debug("Parsed arguments %r", args)

    if args.logo:
        from .logo import clogo
        print(clogo.format(version=__version__))
        sys.exit(0)

    if args.subcmd == 'wheel':
        from .wheel import wheel_main
        try:
            wheel_main(args.ini_file, upload=args.upload,
                     verify_metadata=args.verify_metadata,
                     repo=args.repository)
        except common.ProblemInModule as e:
            sys.exit(e.args[0])
    elif args.subcmd == 'install':
        from .install import Installer
        try:
            Installer(args.ini_file, user=args.user, python=args.python,
                      symlink=args.symlink, deps=args.deps).install()
        except (common.NoDocstringError, common.NoVersionError) as e:
            sys.exit(e.args[0])
    elif args.subcmd == 'installfrom':
        from .installfrom import installfrom
        sys.exit(installfrom(args.location, user=args.user, python=args.python))
    elif args.subcmd == 'register':
        from .upload import register
        meta, mod = common.metadata_and_module_from_ini_path(args.ini_file)
        register(meta, args.repository)
    elif args.subcmd == 'init':
        from .init import TerminalIniter
        TerminalIniter().initialise()
    else:
        ap.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
