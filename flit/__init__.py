"""A simple packaging tool for simple packages."""
import argparse
import logging
import pathlib
import sys

from . import common
from .log import enable_colourful_output

__version__ = '1.2.dev0'

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
    ap.add_argument('-f', '--ini-file', type=pathlib.Path, default='pyproject.toml')
    ap.add_argument('-V', '--version', action='version', version='Flit '+__version__)
    ap.add_argument('--repository',
        help="Name of the repository to upload to (must be in ~/.pypirc)"
    )
    ap.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--logo', action='store_true', help=argparse.SUPPRESS)
    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')

    parser_build = subparsers.add_parser('build',
        help="Build wheel and sdist",
    )

    parser_build.add_argument('--format', action='append',
        help="Select a format to build. Options: 'wheel', 'sdist'"
    )

    parser_publish = subparsers.add_parser('publish',
        help="Upload wheel and sdist",
    )

    parser_publish.add_argument('--format', action='append',
        help="Select a format to publish. Options: 'wheel', 'sdist'"
    )

    parser_install = subparsers.add_parser('install',
        help="Install the package",
    )
    parser_install.add_argument('-s', '--symlink', action='store_true',
        help="Symlink the module/package into site packages instead of copying it"
    )
    parser_install.add_argument('--pth-file', action='store_true',
        help="Add .pth file for the module/package to site packages instead of copying it"
    )
    add_shared_install_options(parser_install)
    parser_install.add_argument('--deps', choices=['all', 'production', 'develop', 'none'], default='all',
        help="Which set of dependencies to install. If --deps=develop, the extras dev, doc, and test are installed"
    )
    parser_install.add_argument('--extras', default=(), type=lambda l: l.split(',') if l else (),
        help="Install the dependencies of these (comma separated) extras additionally to the ones implied by --deps. "
             "--extras=all can be useful in combination with --deps=production, --deps=none precludes using --extras"
    )

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

    args = ap.parse_args(argv)

    cf = args.ini_file
    if args.subcmd != 'init' and cf == pathlib.Path('pyproject.toml')\
            and not cf.is_file():
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

    if args.subcmd == 'build':
        from .build import main
        try:
            main(args.ini_file, formats=set(args.format or []))
        except(common.NoDocstringError) as e:
            sys.exit(e.args[0])
    elif args.subcmd == 'publish':
        from .upload import main
        main(args.ini_file, args.repository, formats=set(args.format or []))

    elif args.subcmd == 'install':
        from .install import Installer
        try:
            Installer(args.ini_file, user=args.user, python=args.python,
                      symlink=args.symlink, deps=args.deps, extras=args.extras,
                      pth=args.pth_file).install()
        except (common.NoDocstringError, common.NoVersionError) as e:
            sys.exit(e.args[0])
    elif args.subcmd == 'installfrom':
        from .installfrom import installfrom
        sys.exit(installfrom(args.location, user=args.user, python=args.python))
    elif args.subcmd == 'init':
        from .init import TerminalIniter
        TerminalIniter().initialise()
    else:
        ap.print_help()
        sys.exit(1)
