"""flit build - build both wheel and sdist"""

import logging
from types import SimpleNamespace

from .sdist import SdistBuilder
from .wheel import wheel_main

log = logging.getLogger(__name__)

def main(ini_file):
    """Build wheel and sdist"""
    wheel_info = wheel_main(ini_file)

    sb = SdistBuilder(ini_file)
    sdist_file = sb.build()

    return SimpleNamespace(wheel=wheel_info,
                           sdist=SimpleNamespace(builder=sb, file=sdist_file))
