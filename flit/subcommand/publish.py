"""
This module contains the implementation of the "installfrom" subcommand.
"""
from ..upload import main

NAME = 'publish'
HELP = "Upload wheel and sdist"


def setup(parser):
    parser.add_argument('--format', action='append',
                        help="Select a format to publish. Options: 'wheel', 'sdist'"
                        )


def run(args):
    main(args.ini_file, args.repository, formats=set(args.format or []))
    return 0
