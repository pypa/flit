import configparser
import os
from pathlib import Path
import tempfile
from unittest import skipIf
import zipfile

import pytest
from testpath import assert_isfile, assert_isdir

from flit.wheel import WheelBuilder, make_wheel_in
from flit.config import EntryPointsConflict

samples_dir = Path(__file__).parent / 'samples'


def unpack(path):
    z = zipfile.ZipFile(str(path))
    t = tempfile.TemporaryDirectory()
    z.extractall(t.name)
    return t

def test_wheel_module(copy_sample):
    td = copy_sample('module1_toml')
    make_wheel_in(td / 'pyproject.toml', td)
    assert_isfile(td / 'module1-0.1-py2.py3-none-any.whl')

def test_wheel_package(copy_sample):
    td = copy_sample('package1')
    make_wheel_in(td / 'pyproject.toml', td)
    assert_isfile(td / 'package1-0.1-py2.py3-none-any.whl')

def test_wheel_src_module(copy_sample):
    td = copy_sample('module3')
    make_wheel_in(td / 'pyproject.toml', td)

    whl_file = td / 'module3-0.1-py2.py3-none-any.whl'
    assert_isfile(whl_file)
    with unpack(whl_file) as unpacked:
        assert_isfile(Path(unpacked, 'module3.py'))
        assert_isdir(Path(unpacked, 'module3-0.1.dist-info'))
        assert_isfile(Path(unpacked, 'module3-0.1.dist-info', 'LICENSE'))

def test_wheel_src_package(copy_sample):
    td = copy_sample('package2')
    make_wheel_in(td / 'pyproject.toml', td)

    whl_file = td / 'package2-0.1-py2.py3-none-any.whl'
    assert_isfile(whl_file)
    with unpack(whl_file) as unpacked:
        print(os.listdir(unpacked))
        assert_isfile(Path(unpacked, 'package2', '__init__.py'))

def test_dist_name(copy_sample):
    td = copy_sample('altdistname')
    make_wheel_in(td / 'pyproject.toml', td)
    res = td / 'package_dist1-0.1-py2.py3-none-any.whl'
    assert_isfile(res)
    with unpack(res) as td_unpack:
        assert_isdir(Path(td_unpack, 'package_dist1-0.1.dist-info'))

def test_entry_points(copy_sample):
    td = copy_sample('entrypoints_valid')
    make_wheel_in(td / 'pyproject.toml', td)
    assert_isfile(td / 'package1-0.1-py2.py3-none-any.whl')
    with unpack(td / 'package1-0.1-py2.py3-none-any.whl') as td_unpack:
        entry_points = Path(td_unpack, 'package1-0.1.dist-info', 'entry_points.txt')
        assert_isfile(entry_points)
        cp = configparser.ConfigParser()
        cp.read(str(entry_points))
        assert 'console_scripts' in cp.sections()
        assert 'myplugins' in cp.sections()

def test_entry_points_conflict(copy_sample):
    td = copy_sample('entrypoints_conflict')
    with pytest.raises(EntryPointsConflict):
        make_wheel_in(td / 'pyproject.toml', td)

def test_wheel_builder():
    # Slightly lower level interface
    with tempfile.TemporaryDirectory() as td:
        target = Path(td, 'sample.whl')
        with target.open('wb') as f:
            wb = WheelBuilder.from_ini_path(samples_dir / 'package1' / 'pyproject.toml', f)
            wb.build()

        assert zipfile.is_zipfile(str(target))
        assert wb.wheel_filename == 'package1-0.1-py2.py3-none-any.whl'

@skipIf(os.name == 'nt', 'Windows does not preserve necessary permissions')
def test_permissions_normed(copy_sample):
    td = copy_sample('module1_toml')

    (td / 'module1.py').chmod(0o620)
    make_wheel_in(td / 'pyproject.toml', td)

    whl = td / 'module1-0.1-py2.py3-none-any.whl'
    assert_isfile(whl)
    with zipfile.ZipFile(str(whl)) as zf:
        info = zf.getinfo('module1.py')
        perms = (info.external_attr >> 16) & 0o777
        assert perms == 0o644, oct(perms)
    whl.unlink()

    # This time with executable bit set
    (td / 'module1.py').chmod(0o720)
    make_wheel_in(td / 'pyproject.toml', td)

    assert_isfile(whl)
    with zipfile.ZipFile(str(whl)) as zf:
        info = zf.getinfo('module1.py')
        perms = (info.external_attr >> 16) & 0o777
        assert perms == 0o755, oct(perms)

        info = zf.getinfo('module1-0.1.dist-info/METADATA')
        perms = (info.external_attr >> 16) & 0o777
        assert perms == 0o644, oct(perms)

def test_compression(tmp_path):
    info = make_wheel_in(samples_dir / 'module1_toml' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    with zipfile.ZipFile(str(info.file)) as zf:
        for name in [
            'module1.py',
            'module1-0.1.dist-info/METADATA',
        ]:
            assert zf.getinfo(name).compress_type == zipfile.ZIP_DEFLATED
