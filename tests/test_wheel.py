import configparser
from pathlib import Path
import shutil
import tempfile
import zipfile

import pytest
from testpath import assert_isfile

from flit.wheel import WheelBuilder, EntryPointsConflict

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

def test_wheel_module():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'module1').build()
    assert_isfile(samples_dir / 'dist/module1-0.1-py2.py3-none-any.whl')

def test_wheel_package():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'package1').build()
    assert_isfile(samples_dir / 'dist/package1-0.1-py2.py3-none-any.whl')

def test_dist_name():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'package3' ).build()
    assert_isfile(samples_dir / 'dist/packagedist1-0.1-py2.py3-none-any.whl')

def test_entry_points():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'package4').build()
    assert_isfile(samples_dir / 'dist/package4-0.1-py2.py3-none-any.whl')
    with unpack(samples_dir / 'dist/package4-0.1-py2.py3-none-any.whl') as td:
        entry_points = Path(td, 'package4-0.1.dist-info', 'entry_points.txt')
        assert_isfile(entry_points)
        cp = configparser.ConfigParser()
        cp.read(str(entry_points))
        assert 'console_scripts' in cp.sections()
        assert 'myplugins' in cp.sections()

def test_entry_points_conflict():
    clear_samples_dist()
    wb = WheelBuilder(samples_dir / 'package5')
    with pytest.raises(EntryPointsConflict):
        wb.build()
