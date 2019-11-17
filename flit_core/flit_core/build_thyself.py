"""Bootstrapping backend

This is *only* meant to build flit_core itself.
Building any other packages occurs through flit_core.buildapi
"""

import io
import os
import os.path as osp
import tempfile

from .common import Metadata, Module, dist_info_name
from .wheel import WheelBuilder, _write_wheel_file, _replace
from .sdist import SdistBuilder

from . import __version__

metadata = Metadata({
    'name': 'flit_core',
    'version': __version__,
    'author': 'Thomas Kluyver & contributors',
    'author_email': 'thomas@kluyver.me.uk',
    'home_page': 'https://github.com/takluyver/flit',
    'summary': ('Distribution-building parts of Flit. '
                    'See flit package for more information'),
    'requires_dist': [
        'pytoml',
    ],
    'requires_python': '>=2.7, !=3.0, !=3.1, !=3.2, != 3.3',
    'classifiers': [
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
})

def get_requires_for_build_wheel(config_settings=None):
    """Returns a list of requirements for building, as strings"""
    return []

def get_requires_for_build_sdist(config_settings=None):
    """Returns a list of requirements for building, as strings"""
    return []

def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    """Creates {metadata_directory}/foo-1.2.dist-info"""
    dist_info = osp.join(metadata_directory,
                         dist_info_name(metadata.name, metadata.version))
    os.mkdir(dist_info)

    with open(osp.join(dist_info, 'WHEEL'), 'w') as f:
        _write_wheel_file(f, supports_py2=metadata.supports_py2)

    with open(osp.join(dist_info, 'METADATA'), 'w') as f:
        metadata.write_metadata_file(f)

    return osp.basename(dist_info)

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Builds a wheel, places it in wheel_directory"""
    srcdir = os.getcwd()
    module = Module('flit_core', srcdir)

    # We don't know the final filename until metadata is loaded, so write to
    # a temporary_file, and rename it afterwards.
    (fd, temp_path) = tempfile.mkstemp(suffix='.whl', dir=str(wheel_directory))
    try:
        with io.open(fd, 'w+b') as fp:
            wb = WheelBuilder(
                srcdir, module, metadata, entrypoints={}, target_fp=fp
            )
            wb.build()

        wheel_path = osp.join(wheel_directory, wb.wheel_filename)
        _replace(temp_path, str(wheel_path))
    except:
        os.unlink(temp_path)
        raise

    return wb.wheel_filename

def build_sdist(sdist_directory, config_settings=None):
    """Builds an sdist, places it in sdist_directory"""
    srcdir = os.getcwd()
    module = Module('flit_core', srcdir)
    reqs_by_extra = {'.none': metadata.requires}

    sb = SdistBuilder(
        module, metadata, srcdir, reqs_by_extra, entrypoints={},
        extra_files=['pyproject.toml']
    )
    path = sb.build(sdist_directory)
    return osp.basename(path)

