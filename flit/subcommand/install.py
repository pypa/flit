"""
This module contains the implementation for the "install" subcommand

This module also contains a definition of ``add_shared_install_options`` which
can be used to set up additional arguments for an "install-type" subcommand.
"""

import sys
from ..install import Installer
from .. import common

NAME = 'install'
HELP = "Install the package"


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


def setup(parser):
    parser.add_argument('-s', '--symlink', action='store_true',
        help="Symlink the module/package into site packages instead of copying it"
    )
    parser.add_argument('--pth-file', action='store_true',
        help="Add .pth file for the module/package to site packages instead of copying it"
    )
    parser.add_argument('--deps', choices=['all', 'production', 'develop', 'none'], default='all',
        help="Which set of dependencies to install. If --deps=develop, the extras dev, doc, and test are installed"
    )
    parser.add_argument('--extras', default=(), type=lambda l: l.split(',') if l else (),
        help="Install the dependencies of these (comma separated) extras additionally to the ones implied by --deps. "
             "--extras=all can be useful in combination with --deps=production, --deps=none precludes using --extras"
    )
    add_shared_install_options(parser)


def run(args):
    try:
        Installer(args.ini_file, user=args.user, python=args.python,
                    symlink=args.symlink, deps=args.deps, extras=args.extras,
                    pth=args.pth_file).install()
    except (common.NoDocstringError, common.NoVersionError) as e:
        return e.args[0]
    return 0
