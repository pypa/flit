"""A simple packaging tool for simple packages."""
import argparse
import logging
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Optional

from flit_core import common
from .config import ConfigError
from .log import enable_colourful_output

__version__ = '3.10.1'

log = logging.getLogger(__name__)


class PythonNotFoundError(FileNotFoundError): pass


def find_python_executable(python: Optional[str] = None) -> str:
    """Returns an absolute filepath to the executable of Python to use."""
    if not python:
        python = os.environ.get("FLIT_INSTALL_PYTHON")
    if not python:
        return sys.executable
    if os.path.isdir(python):
        # Assume it's a virtual environment and look for the environment's
        # Python executable.  This is the same behavior used by pip.
        #
        # Try both Unix and Windows paths in case of odd cases like cygwin.
        for exe in ("bin/python", "Scripts/python.exe"):
            py = os.path.join(python, exe)
            if os.path.exists(py):
                return os.path.abspath(py)
    if os.path.isabs(python):  # sys.executable is absolute too
        return python
    # get absolute filepath of {python}
    # shutil.which may give a different result to the raw subprocess call
    # see https://github.com/pypa/flit/pull/300 and https://bugs.python.org/issue38905
    resolved_python = shutil.which(python)
    if resolved_python is None:
        raise PythonNotFoundError("Unable to resolve Python executable {!r}".format(python))
    try:
        return subprocess.check_output(
            [resolved_python, "-c", "import sys; print(sys.executable)"],
            universal_newlines=True,
        ).strip()
    except Exception as e:
        raise PythonNotFoundError(
            "{} occurred trying to find the absolute filepath of Python executable {!r} ({!r})".format(
                e.__class__.__name__, python, resolved_python
            )
        ) from e


def add_shared_install_options(parser: argparse.ArgumentParser):
    parser.add_argument('--user', action='store_true', default=None,
        help="Do a user-local install (default if site.ENABLE_USER_SITE is True)"
    )
    parser.add_argument('--env', action='store_false', dest='user',
        help="Install into sys.prefix (default if site.ENABLE_USER_SITE is False, i.e. in virtualenvs)"
    )
    parser.add_argument('--python',
        help="Target Python executable, if different from the one running flit"
    )
    parser.add_argument('--deps', choices=['all', 'production', 'develop', 'none'], default='all',
        help="Which set of dependencies to install. If --deps=develop, the extras dev, doc, and test are installed"
    )
    parser.add_argument('--only-deps', action='store_true',
        help="Install only dependencies of this package, and not the package itself"
    )
    parser.add_argument('--extras', default=(), type=lambda l: l.split(',') if l else (),
        help="Install the dependencies of these (comma separated) extras additionally to the ones implied by --deps. "
             "--extras=all can be useful in combination with --deps=production, --deps=none precludes using --extras"
    )


def add_shared_build_options(parser: argparse.ArgumentParser):
    parser.add_argument('--format', action='append',
        help="Select a format to publish. Options: 'wheel', 'sdist'"
    )

    setup_py_grp = parser.add_mutually_exclusive_group()

    setup_py_grp.add_argument('--setup-py', action='store_true',
        help=("Generate a setup.py file in the sdist. "
              "The sdist will work with older tools that predate PEP 517. "
            )
    )

    setup_py_grp.add_argument('--no-setup-py', action='store_true',
        help=("Don't generate a setup.py file in the sdist. This is the default. "
              "The sdist will only work with tools that support PEP 517, "
              "but the wheel will still be usable by any compatible tool."
             )
    )

    vcs_grp = parser.add_mutually_exclusive_group()

    vcs_grp.add_argument('--use-vcs', action='store_true',
        help=("Choose which files to include in the sdist using git or hg. "
              "This is a convenient way to include all checked-in files, like "
              "tests and doc source files, in your sdist, but requires that git "
              "or hg is available on the command line. This is currently the "
              "default, but it will change in a future version. "
             )
    )

    vcs_grp.add_argument('--no-use-vcs', action='store_true',
        help=("Select the files to include in the sdist without using git or hg. "
              "This should include all essential files to install and use your "
              "package; see the documentation for precisely what is included. "
              "This will become the default in a future version."
             )
    )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--ini-file', type=pathlib.Path, default='pyproject.toml')
    ap.add_argument('-V', '--version', action='version', version='Flit '+__version__)
    # --repository now belongs on 'flit publish' - it's still here for
    # compatibility with scripts passing it before the subcommand.
    ap.add_argument('--repository', dest='deprecated_repository', help=argparse.SUPPRESS)
    ap.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--logo', action='store_true', help=argparse.SUPPRESS)
    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')

    # flit build --------------------------------------------
    parser_build = subparsers.add_parser('build',
        help="Build wheel and sdist",
    )

    add_shared_build_options(parser_build)

    # flit publish --------------------------------------------
    parser_publish = subparsers.add_parser('publish',
        help="Upload wheel and sdist",
    )

    add_shared_build_options(parser_publish)

    parser_publish.add_argument('--pypirc',
        help="The .pypirc config file to be used. DEFAULT = \"~/.pypirc\""
    )

    parser_publish.add_argument('--repository',
        help="Name of the repository to upload to (must be in the specified .pypirc file)"
    )

    # flit install --------------------------------------------
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

    # flit init --------------------------------------------
    parser_init = subparsers.add_parser('init',
        help="Prepare pyproject.toml for a new package"
    )

    args = ap.parse_args(argv)

    if args.ini_file.suffix == '.ini':
        sys.exit("flit.ini format is no longer supported. You can use "
                 "'python3 -m flit.tomlify' to convert it to pyproject.toml")

    if args.subcmd not in {'init'} and not args.ini_file.is_file():
        sys.exit('Config file {} does not exist'.format(args.ini_file))

    enable_colourful_output(logging.DEBUG if args.debug else logging.INFO)

    log.debug("Parsed arguments %r", args)

    if args.logo:
        from .logo import clogo
        print(clogo.format(version=__version__))
        sys.exit(0)

    def gen_setup_py():
        if not (args.setup_py or args.no_setup_py):
            return False
        return args.setup_py

    def sdist_use_vcs():
        return not args.no_use_vcs

    if args.subcmd == 'build':
        from .build import main
        try:
            main(args.ini_file, formats=set(args.format or []),
                 gen_setup_py=gen_setup_py(), use_vcs=sdist_use_vcs())
        except(common.NoDocstringError, common.VCSError, common.NoVersionError) as e:
            sys.exit(e.args[0])
    elif args.subcmd == 'publish':
        if args.deprecated_repository:
            log.warning("Passing --repository before the 'upload' subcommand is deprecated: pass it after")
        repository = args.repository or args.deprecated_repository
        from .upload import main
        main(args.ini_file, repository, args.pypirc, formats=set(args.format or []),
                gen_setup_py=gen_setup_py(), use_vcs=sdist_use_vcs())

    elif args.subcmd == 'install':
        from .install import Installer
        try:
            python = find_python_executable(args.python)
            installer = Installer.from_ini_path(
                args.ini_file,
                user=args.user,
                python=python,
                symlink=args.symlink,
                deps=args.deps,
                extras=args.extras,
                pth=args.pth_file
            )
            if args.only_deps:
                installer.install_requirements()
            else:
                installer.install()
        except (ConfigError, PythonNotFoundError, common.NoDocstringError, common.NoVersionError) as e:
            sys.exit(e.args[0])

    elif args.subcmd == 'init':
        from .init import TerminalIniter
        TerminalIniter().initialise()
    else:
        ap.print_help()
        sys.exit(1)
