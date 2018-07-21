from contextlib import contextmanager
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from testpath import assert_isfile, assert_isdir
import zipfile

from flit import buildapi

samples_dir = Path(__file__).parent / 'samples'

@contextmanager
def cwd(directory):
    prev = os.getcwd()
    os.chdir(str(directory))
    try:
        yield
    finally:
        os.chdir(prev)

def test_get_build_requires():
    expected = ["requests >= 2.18", "docutils"]
    with cwd(samples_dir / 'pep517'):
        assert buildapi.get_requires_for_build_wheel() == expected
        assert buildapi.get_requires_for_build_sdist() == expected

def test_build_wheel():
    with TemporaryDirectory() as td, cwd(samples_dir / 'pep517'):
        filename = buildapi.build_wheel(td)
        assert filename.endswith('.whl'), filename
        assert_isfile(Path(td, filename))
        assert zipfile.is_zipfile(str(Path(td, filename)))

def test_build_sdist():
    with TemporaryDirectory() as td, cwd(samples_dir / 'pep517'):
        filename = buildapi.build_sdist(td)
        assert filename.endswith('.tar.gz'), filename
        assert_isfile(Path(td, filename))
        assert tarfile.is_tarfile(str(Path(td, filename)))

def test_prepare_metadata_for_build_wheel():
    with TemporaryDirectory() as td, cwd(samples_dir / 'pep517'):
        dirname = buildapi.prepare_metadata_for_build_wheel(td)
        assert dirname.endswith('.dist-info'), dirname
        assert_isdir(Path(td, dirname))
        assert_isfile(Path(td, dirname, 'METADATA'))
