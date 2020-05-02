import logging

import flit_core.wheel as core_wheel

log = logging.getLogger(__name__)

def make_wheel_in(ini_path, wheel_directory):
    return core_wheel.make_wheel_in(ini_path, wheel_directory)

class WheelBuilder(core_wheel.WheelBuilder):
    pass

