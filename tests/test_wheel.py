import pathlib

from testpath import assert_isfile

from flit import wheel

samples_dir = pathlib.Path(__file__).parent / 'samples'

def test_wheel_module():
    wheel(samples_dir / 'module1-pkg.ini')
    assert_isfile(str(samples_dir / 'dist/module1-0.1-py2.py3-none-any.whl'))

def test_wheel_package():
    wheel(samples_dir / 'package1-pkg.ini')
    assert_isfile(str(samples_dir / 'dist/package1-0.1-py2.py3-none-any.whl'))
