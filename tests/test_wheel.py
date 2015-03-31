import pathlib
import shutil

from testpath import assert_isfile

from flit.wheel import WheelBuilder

samples_dir = pathlib.Path(__file__).parent / 'samples'

def clear_samples_dist():
    try:
        shutil.rmtree(str(samples_dir / 'dist'))
    except FileNotFoundError:
        pass

def test_wheel_module():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'module1-pkg.ini').build()
    assert_isfile(str(samples_dir / 'dist/module1-0.1-py2.py3-none-any.whl'))

def test_wheel_package():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'package1-pkg.ini').build()
    assert_isfile(str(samples_dir / 'dist/package1-0.1-py2.py3-none-any.whl'))

def test_dist_name():
    clear_samples_dist()
    WheelBuilder(samples_dir / 'altdistname.ini').build()
    assert_isfile(str(samples_dir / 'dist/packagedist1-0.1-py2.py3-none-any.whl'))
