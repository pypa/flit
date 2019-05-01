"""
This module contains the implementation for the "init" subcommand
"""

from ..init import TerminalIniter

NAME = 'init'
HELP = "Prepare pyproject.toml for a new package"


def setup(parser):
    pass


def run(args):
    TerminalIniter().initialise()
    return 0
