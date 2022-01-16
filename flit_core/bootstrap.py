"""Install flit_core without using any other tools.

Normally, you would install flit_core with pip like any other Python package.
This script is meant to help with 'bootstrapping' other packaging
systems, where you may need flit_core to build other packaging tools.

Pass a path to the site-packages directory or equivalent where the package
should be placed. If omitted, this defaults to the site-packages directory
of the Python running the script.
"""
import argparse
import sys
import sysconfig
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from flit_core.wheel import add_wheel_arguments, build_flit_wheel

srcdir = Path(__file__).parent.resolve()

def extract_wheel(whl_path, dest):
    print("Installing to", dest.resolve())
    with ZipFile(whl_path) as zf:
        zf.extractall(dest)

def add_install_arguments(parser):
    parser.add_argument(
        '--wheeldir',
        '-w',
        type=str,
        help=f'wheel dist directory (defaults to {srcdir.joinpath("dist").resolve()})',
    )
    purelib = Path(sysconfig.get_path('purelib'))
    parser.add_argument(
        '--installdir',
        '-i',
        type=Path,
        default=purelib,
        help=f'installdir directory (defaults to {purelib.resolve()}',
    )
    return parser

def get_dist_wheel(wheeldir):
    wheel_path = Path(wheeldir) if wheeldir is not None else srcdir.joinpath('dist')
    wheel_glob = wheel_path.glob('flit_core-*.whl')
    return next(wheel_glob, None)

def build(args):
    print("Building wheel")
    outdir = srcdir.joinpath('dist') if args.outdir is None else Path(args.outdir)
    whl_fname = build_flit_wheel(srcdir, outdir)
    print("Wheel built", outdir.joinpath(whl_fname).resolve())

def install(args):
    dist_wheel = get_dist_wheel(args.wheeldir)

    # User asked to install wheel but none was found
    if dist_wheel is None and args.wheeldir is not None:
        print(f"No wheel found in {Path(args.wheeldir).resolve()}")
        sys.exit(1)

    if dist_wheel is not None:
        print("Installing from wheel", dist_wheel.resolve())
        # Extract the prebuilt wheel
        extract_wheel(dist_wheel, args.installdir)
    else:
        # No prebuilt wheel found, build in temp dir
        with TemporaryDirectory(prefix='flit_core-bootstrap-') as td:
            whl_fname = build_flit_wheel(srcdir, Path(td))
            whl_path = Path(td).joinpath(whl_fname)
            extract_wheel(whl_path, args.installdir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    build_parser = subparsers.add_parser('build')
    build_parser = add_wheel_arguments(build_parser, srcdir)
    build_parser.set_defaults(func=build)

    install_parser = subparsers.add_parser('install')
    install_parser = add_install_arguments(install_parser)
    install_parser.set_defaults(func=install)

    args = parser.parse_args()
    args.func(args)
