"""Build flit_core to upload to PyPI.

Normally, this should only be used by me when making a release.
"""
import os
import sys
from pathlib import Path

cwd = Path(__file__).parent.resolve()
os.chdir(cwd)
sys.path.append(str(cwd.parent))
# Allow importing from flit without requests(not needed)
sys.modules['requests'] = False
from flit.sdist import SdistBuilder
from flit_core import build_thyself
from flit_core.build_thyself import metadata
from flit_core.common import Module


def build_release_sdist(sdist_directory, config_settings=None):
    """Builds an sdist, places it in sdist_directory"""
    cwd = Path.cwd()
    module = Module('flit_core', cwd)
    reqs_by_extra = {'.none': metadata.requires}

    sb = SdistBuilder(
        module, metadata, cwd, reqs_by_extra, entrypoints={},
        extra_files=['pyproject.toml', 'build_dists.py']
    )
    path = sb.build(Path(sdist_directory), gen_setup_py=True)
    return path.name


print("Building sdist")
sdist_fname = build_release_sdist('dist/')
print(os.path.join('dist', sdist_fname))

print("\nBuilding wheel")
whl_fname = build_thyself.build_wheel('dist/')
print(os.path.join('dist', whl_fname))
