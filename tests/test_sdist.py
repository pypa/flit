from pathlib import Path
import pytest
from shutil import which
from tempfile import TemporaryDirectory
from testpath import assert_isfile

from flit import sdist

samples_dir = Path(__file__).parent / 'samples'

def test_auto_packages():
    packages, pkg_data = sdist.auto_packages(str(samples_dir / 'package1'))
    assert packages == ['package1', 'package1.subpkg', 'package1.subpkg2']
    assert pkg_data == {'': ['*'],
                        'package1': ['data_dir/*'],
                        'package1.subpkg': ['sp_data_dir/*'],
                       }

def test_make_sdist():
    # Smoke test of making a complete sdist
    if not which('git'):
        pytest.skip("requires git")
    builder = sdist.SdistBuilder(samples_dir / 'package1-pkg.ini')
    with TemporaryDirectory() as td:
        td = Path(td)
        builder.build(td)
        assert_isfile(td / 'package1-0.1.tar.gz')
