from contextlib import contextmanager
import os
import os.path as osp
import tarfile
from testpath import assert_isfile, assert_isdir
from testpath.tempdir import TemporaryDirectory
import zipfile

from flit_core import buildapi

samples_dir = osp.join(osp.dirname(__file__), 'samples')

@contextmanager
def cwd(directory):
    prev = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(prev)

def test_get_build_requires():
    expected = ["requests >= 2.18", "docutils"]
    with cwd(osp.join(samples_dir,'pep517')):
        assert buildapi.get_requires_for_build_wheel() == expected
        assert buildapi.get_requires_for_build_sdist() == expected

def test_build_wheel():
    with TemporaryDirectory() as td, cwd(osp.join(samples_dir,'pep517')):
        filename = buildapi.build_wheel(td)
        assert filename.endswith('.whl'), filename
        assert_isfile(osp.join(td, filename))
        assert zipfile.is_zipfile(osp.join(td, filename))

def test_build_sdist():
    with TemporaryDirectory() as td, cwd(osp.join(samples_dir,'pep517')):
        filename = buildapi.build_sdist(td)
        assert filename.endswith('.tar.gz'), filename
        assert_isfile(osp.join(td, filename))
        assert tarfile.is_tarfile(osp.join(td, filename))

def test_prepare_metadata_for_build_wheel():
    with TemporaryDirectory() as td, cwd(osp.join(samples_dir,'pep517')):
        dirname = buildapi.prepare_metadata_for_build_wheel(td)
        assert dirname.endswith('.dist-info'), dirname
        assert_isdir(osp.join(td, dirname))
        assert_isfile(osp.join(td, dirname, 'METADATA'))
