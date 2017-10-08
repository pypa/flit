"""flit build - build both wheel and sdist"""

import logging
from types import SimpleNamespace

from .sdist import SdistBuilder
from .wheel import wheel_main

log = logging.getLogger(__name__)

ALL_FORMATS = {'wheel', 'sdist'}

def main(ini_file, formats=None):
    """Build wheel and sdist"""
    if not formats:
        formats = ALL_FORMATS
    elif not formats.issubset(ALL_FORMATS):
        raise ValueError("Unknown package formats: {}".format(formats - ALL_FORMATS))

    if 'wheel' in formats:
        wheel_info = wheel_main(ini_file)
    else:
        wheel_info = None

    if 'sdist' in formats:
        sb = SdistBuilder(ini_file)
        sdist_file = sb.build()
        sdist_info = SimpleNamespace(builder=sb, file=sdist_file)
    else:
        sdist_info = None

    return SimpleNamespace(wheel=wheel_info, sdist=sdist_info)
