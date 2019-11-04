import configparser
import os
from pathlib import Path
import shutil
import tempfile
from unittest import skipIf
import zipfile

import pytest
from testpath import assert_isfile, assert_isdir

from flit.wheel import wheel_main, WheelBuilder
from flit.inifile import EntryPointsConflict

samples_dir = Path(__file__).parent / 'samples'

def clear_samples_dist():
    try:
        shutil.rmtree(str(samples_dir / 'dist'))
    except FileNotFoundError:
        pass


def unpack(path):
    z = zipfile.ZipFile(str(path))
    t = tempfile.TemporaryDirectory()
    z.extractall(t.name)
    return t

def test_wheel_module(copy_sample):
    td = copy_sample('module1')
    wheel_main(td / 'flit.ini')
    assert_isfile(td / 'dist/module1-0.1-py2.py3-none-any.whl')

def test_wheel_package():
    clear_samples_dist()
    wheel_main(samples_dir / 'package1-pkg.ini')
    assert_isfile(samples_dir / 'dist/package1-0.1-py2.py3-none-any.whl')

def test_wheel_src_module(copy_sample):
    td = copy_sample('module3')
    wheel_main(td / 'flit.ini')
    assert_isfile(td / 'dist/module3-0.1-py2.py3-none-any.whl')

def test_wheel_src_package(copy_sample):
    td = copy_sample('package2')
    wheel_main(td / 'package2-pkg.ini')
    assert_isfile(td / 'dist/package2-0.1-py2.py3-none-any.whl')

def test_dist_name(copy_sample):
    td = copy_sample('altdistname')
    wheel_main(td / 'flit.ini')
    res = td / 'dist/package_dist1-0.1-py2.py3-none-any.whl'
    assert_isfile(res)
    with unpack(res) as td_unpack:
        assert_isdir(Path(td_unpack, 'package_dist1-0.1.dist-info'))

def test_entry_points():
    clear_samples_dist()
    wheel_main(samples_dir / 'entrypoints_valid.ini')
    assert_isfile(samples_dir / 'dist/package1-0.1-py2.py3-none-any.whl')
    with unpack(samples_dir / 'dist/package1-0.1-py2.py3-none-any.whl') as td:
        entry_points = Path(td, 'package1-0.1.dist-info', 'entry_points.txt')
        assert_isfile(entry_points)
        cp = configparser.ConfigParser()
        cp.read(str(entry_points))
        assert 'console_scripts' in cp.sections()
        assert 'myplugins' in cp.sections()

def test_entry_points_conflict():
    clear_samples_dist()
    with pytest.raises(EntryPointsConflict):
        wheel_main(samples_dir / 'entrypoints_conflict.ini')

def test_wheel_builder():
    # Slightly lower level interface
    with tempfile.TemporaryDirectory() as td:
        target = Path(td, 'sample.whl')
        with target.open('wb') as f:
            wb = WheelBuilder.from_ini_path(samples_dir / 'package1-pkg.ini', f)
            wb.build()

        assert zipfile.is_zipfile(str(target))
        assert wb.wheel_filename == 'package1-0.1-py2.py3-none-any.whl'

@skipIf(os.name == 'nt', 'Windows does not preserve necessary permissions')
def test_permissions_normed(copy_sample):
    td = copy_sample('module1')

    Path(td, 'module1.py').chmod(0o620)
    wheel_main(Path(td, 'flit.ini'))

    whl = Path(td, 'dist', 'module1-0.1-py2.py3-none-any.whl')
    assert_isfile(whl)
    with zipfile.ZipFile(str(whl)) as zf:
        info = zf.getinfo('module1.py')
        perms = (info.external_attr >> 16) & 0o777
        assert perms == 0o644, oct(perms)
    whl.unlink()

    # This time with executable bit set
    Path(td, 'module1.py').chmod(0o720)
    wheel_main(Path(td, 'flit.ini'))

    assert_isfile(whl)
    with zipfile.ZipFile(str(whl)) as zf:
        info = zf.getinfo('module1.py')
        perms = (info.external_attr >> 16) & 0o777
        assert perms == 0o755, oct(perms)
