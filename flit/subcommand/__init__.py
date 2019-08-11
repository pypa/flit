"""
The "subcommand" package contains implementations for CLI commands in flit.

Subcommands must:

* Contain an implementation in ``flit/subcommand/<name>.py``
* Be registered using ``flit.subcommand.register`` before parsing the arguments

Each subcommand module must contain the following names:

* NAME: the name of the command which is exposed in the CLI args (this is what
  the user types to trigger that subcommand).
* HELP: A short 1-line help which is displayed when the user runs
  ``flit --help``
* setup: A callable which sets up the subparsers. As a single argument it gets
  a reference to the sub-parser. No return required.
* run: A callable which gets executed when the subcommand is selected by the
  end-user. As a single argument it gets a reference to the root
  argument-parser. It should return an integer representing the exit-code of
  the application.
"""
from importlib import import_module


def register(main_parser, module_name):
    """
    This registers a new subcommand with the main argument parser.

    :param main_parser: A reference to the main argument parser instance.
    :param module_name: The base-name of the subcommand module. If a module is
        added as ``flit/subcommand/foo.py``, this should be ``foo``. This value
        is used to dynamically import the subcommend so it must be a valid
        module name.
    """
    subcmd = import_module('flit.subcommand.%s' % module_name)
    parser = main_parser.add_parser(subcmd.NAME,help=subcmd.HELP)
    parser.set_defaults(subcmd_entrypoint=subcmd.run)
    subcmd.setup(parser)
