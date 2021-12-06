"""Install flit_core without using any other tools.

Normally, you would install flit_core with pip like any other Python package.
This script is meant to help with 'bootstrapping' other packaging
systems, where you may need flit_core to build other packaging tools.

Pass a path to the site-packages directory or equivalent where the package
should be placed. If omitted, this defaults to the site-packages directory
of the Python running the script.
"""
import os
import sys
import sysconfig
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from flit_core import build_thyself

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if len(sys.argv) == 2:
    dest = sys.argv[1]
    if not os.path.isdir(dest):
        sys.exit("Destination path must already be a directory")
elif len(sys.argv) == 1:
    dest = sysconfig.get_path('purelib')
else:
    sys.exit("Specify 0 or 1 arguments (destination directory)")

with TemporaryDirectory(prefix='flit_core-bootstrap-') as td:
    print("Building wheel")
    whl_fname = build_thyself.build_wheel(td)
    whl_path = os.path.join(td, whl_fname)

    print("Installing to", dest)
    with ZipFile(whl_path) as zf:
        zf.extractall(dest)
