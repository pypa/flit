"""Install flit_core without using any other tools.

Normally, you would install flit_core with pip like any other Python package.
This script is meant to help with 'bootstrapping' other packaging
systems, where you may need flit_core to build other packaging tools.

Use 'python -m flit_core.wheel' to make a wheel, then:

    python bootstrap_install.py flit_core-3.6.0-py3-none-any.whl

To install for something other than the Python running the script, pass a
site-packages or equivalent directory with the --installdir option.
"""
import argparse
import sys
import sysconfig
from pathlib import Path
from zipfile import ZipFile

def extract_wheel(whl_path, dest):
    print("Installing to", dest)
    with ZipFile(whl_path) as zf:
        zf.extractall(dest)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'wheel',
        type=Path,
        help=f'flit_core wheel to install (.whl file)',
    )
    purelib = Path(sysconfig.get_path('purelib')).resolve()
    parser.add_argument(
        '--installdir',
        '-i',
        type=Path,
        default=purelib,
        help=f'installdir directory (defaults to {purelib})',
    )
    parser.add_argument(
        '--install-root',
        type=Path,
        default=None,
        help='if given, installdir is considered to be under this'
    )

    args = parser.parse_args()

    if not args.wheel.name.startswith('flit_core-'):
        sys.exit("Use this script only for flit_core wheels")
    if args.install_root:
        installdir = args.install_root / args.installdir.relative_to("/")
    else:
        installdir = args.installdir

    installdir.mkdir(parents=True, exist_ok=True)
    extract_wheel(args.wheel, installdir)
