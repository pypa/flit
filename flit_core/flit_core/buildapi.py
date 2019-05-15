"""PEP-517 compliant buildsystem API"""
import logging
from pathlib import Path

from .common import Module, make_metadata, write_entry_points, dist_info_name
from .inifile import read_pkg_ini
from .wheel import make_wheel_in, _write_wheel_file
from .sdist import SdistBuilder

log = logging.getLogger(__name__)

# PEP 517 specifies that the CWD will always be the source tree
pyproj_toml = Path('pyproject.toml')

def get_requires_for_build_wheel(config_settings=None):
    """Returns a list of requirements for building, as strings"""
    info = read_pkg_ini(pyproj_toml)
    return info['metadata'].get('requires_dist', [])

# For now, we require all dependencies to build either a wheel or an sdist.
get_requires_for_build_sdist = get_requires_for_build_wheel

def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    """Creates {metadata_directory}/foo-1.2.dist-info"""
    ini_info = read_pkg_ini(pyproj_toml)
    module = Module(ini_info['module'], Path.cwd())
    metadata = make_metadata(module, ini_info)

    dist_info = Path(metadata_directory,
                     dist_info_name(metadata.name, metadata.version))
    dist_info.mkdir()

    with (dist_info / 'WHEEL').open('w') as f:
        _write_wheel_file(f, supports_py2=metadata.supports_py2)

    with (dist_info / 'METADATA').open('w') as f:
        metadata.write_metadata_file(f)

    if ini_info['entrypoints']:
        with (dist_info / 'entry_points.txt').open('w') as f:
            write_entry_points(ini_info['entrypoints'], f)

    return dist_info.name

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Builds a wheel, places it in wheel_directory"""
    info = make_wheel_in(pyproj_toml, Path(wheel_directory))
    return info.file.name

def build_sdist(sdist_directory, config_settings=None):
    """Builds an sdist, places it in sdist_directory"""
    path = SdistBuilder(pyproj_toml).build(Path(sdist_directory))
    return path.name
