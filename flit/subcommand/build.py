"""
This module contains the implementation for the "build" subcommand.
"""
import sys

from .. import common
from ..build import main

NAME = 'build'
HELP = "Build wheel and sdist"


def setup(parser):
    parser.add_argument(
        '--format', action='append',
        help="Select a format to build. Options: 'wheel', 'sdist'"
    )


def run(args):
    try:
        main(args.ini_file, formats=set(args.format or []))
    except(common.NoDocstringError, common.VCSError, common.NoVersionError) as e:
        return e.args[0]
    return 0
