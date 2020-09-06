"""Build flit_core to upload to PyPI.

Normally, this should only be used by me when making a release.
"""
import os

from flit_core import build_thyself

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("Building sdist")
sdist_fname = build_thyself.build_sdist('dist/')
print(os.path.join('dist', sdist_fname))

print("\nBuilding wheel")
whl_fname = build_thyself.build_wheel('dist/')
print(os.path.join('dist', whl_fname))
