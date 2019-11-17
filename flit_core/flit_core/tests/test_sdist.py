from io import BytesIO
import os.path as osp
import tarfile
from testpath import assert_isfile
from testpath.tempdir import TemporaryDirectory

from flit_core import sdist

samples_dir = osp.join(osp.dirname(__file__), 'samples')

def test_make_sdist():
    # Smoke test of making a complete sdist
    builder = sdist.SdistBuilder.from_ini_path(osp.join(samples_dir, 'package1-pkg.ini'))
    with TemporaryDirectory() as td:
        builder.build(td)
        assert_isfile(osp.join(td, 'package1-0.1.tar.gz'))


def test_clean_tarinfo():
    with tarfile.open(mode='w', fileobj=BytesIO()) as tf:
        ti = tf.gettarinfo(osp.join(samples_dir, 'module1.py'))
    cleaned = sdist.clean_tarinfo(ti, mtime=42)
    assert cleaned.uid == 0
    assert cleaned.uname == ''
    assert cleaned.mtime == 42


def test_include_exclude():
    builder = sdist.SdistBuilder.from_ini_path(
        osp.join(samples_dir, 'inclusion', 'pyproject.toml')
    )
    files = builder.apply_includes_excludes(builder.select_files())

    assert osp.join('doc', 'test.rst') in files
    assert osp.join('doc', 'test.txt') not in files
    assert osp.join('doc', 'subdir', 'test.txt') in files
