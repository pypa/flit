"""flit build - build both wheel and sdist"""

from contextlib import contextmanager
import logging
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys

from .config import read_flit_config, ConfigError
from .sdist import SdistBuilder
from .wheel import make_wheel_in

log = logging.getLogger(__name__)

ALL_FORMATS = {'wheel', 'sdist'}

@contextmanager
def unpacked_tarball(path):
    tf = tarfile.open(str(path))
    with TemporaryDirectory() as tmpdir:
        tf.extractall(tmpdir)
        files = os.listdir(tmpdir)
        assert len(files) == 1, files
        yield os.path.join(tmpdir, files[0])

def main(ini_file: Path, formats=None, gen_setup_py=True, use_vcs=True):
    """Build wheel and sdist"""
    if not formats:
        formats = ALL_FORMATS
    elif not formats.issubset(ALL_FORMATS):
        raise ValueError("Unknown package formats: {}".format(formats - ALL_FORMATS))

    sdist_info = wheel_info = None
    dist_dir = ini_file.parent / 'dist'
    dist_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Load the config file to make sure it gets validated
        read_flit_config(ini_file)

        if 'sdist' in formats:
            sb = SdistBuilder.from_ini_path(ini_file, use_vcs=use_vcs)
            sdist_file = sb.build(dist_dir, gen_setup_py=gen_setup_py)
            sdist_info = SimpleNamespace(builder=sb, file=sdist_file)
            # When we're building both, build the wheel from the unpacked sdist.
            # This helps ensure that the sdist contains all the necessary files.
            if 'wheel' in formats:
                with unpacked_tarball(sdist_file) as tmpdir:
                    log.debug('Building wheel from unpacked sdist %s', tmpdir)
                    tmp_ini_file = Path(tmpdir, ini_file.name)
                    wheel_info = make_wheel_in(tmp_ini_file, dist_dir)
        elif 'wheel' in formats:
            wheel_info = make_wheel_in(ini_file, dist_dir)
    except ConfigError as e:
        sys.exit('Config error: {}'.format(e))

    return SimpleNamespace(wheel=wheel_info, sdist=sdist_info)
