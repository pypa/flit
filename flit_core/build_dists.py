"""Build flit_core to upload to PyPI.

Normally, this should only be used by me when making a release.
"""
import os

from flit_core import buildapi

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("Building sdist")
sdist_fname = buildapi.build_sdist('dist/')
print(os.path.join('dist', sdist_fname))

print("\nBuilding wheel")
whl_fname = buildapi.build_wheel('dist/')
print(os.path.join('dist', whl_fname))
