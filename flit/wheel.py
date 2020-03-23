import logging
from pathlib import Path

import flit_core.wheel as core_wheel

log = logging.getLogger(__name__)

def make_wheel_in(ini_path, wheel_directory):
    info = core_wheel.make_wheel_in(str(ini_path), str(wheel_directory))
    info.file = Path(info.file)
    return info


class WheelBuilder(core_wheel.WheelBuilder):
    @classmethod
    def from_ini_path(cls, ini_path, target_fp):
        return super().from_ini_path(str(ini_path), target_fp)

