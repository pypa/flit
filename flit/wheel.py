import logging
from pathlib import Path

import flit_core.wheel as core_wheel

log = logging.getLogger(__name__)

def make_wheel_in(ini_path, wheel_directory):
    info = core_wheel.make_wheel_in(str(ini_path), str(wheel_directory))
    info.file = Path(info.file)
    return info

def wheel_main(ini_path, upload=False, verify_metadata=False, repo='pypi'):
    """Build a wheel in the dist/ directory, and optionally upload it.
    """
    dist_dir = ini_path.parent / 'dist'
    try:
        dist_dir.mkdir()
    except FileExistsError:
        pass

    wheel_info = make_wheel_in(ini_path, dist_dir)

    if verify_metadata:
        from .upload import verify
        log.warning("'flit wheel --verify-metadata' is deprecated.")
        verify(wheel_info.builder.metadata, repo)

    if upload:
        from .upload import do_upload
        log.warning("'flit wheel --upload' is deprecated; use 'flit publish' instead.")
        do_upload(Path(wheel_info.file), wheel_info.builder.metadata, repo)

    return wheel_info


class WheelBuilder(core_wheel.WheelBuilder):
    @classmethod
    def from_ini_path(cls, ini_path, target_fp):
        return super().from_ini_path(str(ini_path), target_fp)

