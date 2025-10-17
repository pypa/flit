import ast
from os.path import join as pjoin
from pathlib import Path
from unittest.mock import patch
import pytest
from shutil import which, copytree
import sys
import tarfile
from tempfile import TemporaryDirectory
from testpath import assert_isfile, MockCommand

from flit import sdist, common

samples_dir = Path(__file__).parent / 'samples'

def test_auto_packages():
    module = common.Module('package1', samples_dir / 'package1')
    packages, pkg_data = sdist.auto_packages(module)
    assert packages == ['package1', 'package1.subpkg', 'package1.subpkg2']
    assert pkg_data == {'': ['*'],
                        'package1': ['data_dir/*'],
                        'package1.subpkg': ['sp_data_dir/*'],
                       }

def test_make_sdist():
    # Smoke test of making a complete sdist
    if not which('git'):
        pytest.skip("requires git")
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1' / 'pyproject.toml')
    with TemporaryDirectory() as td:
        td = Path(td)
        builder.build(td)
        sdist_file = td / 'package1-0.1.tar.gz'
        assert_isfile(sdist_file)

        with tarfile.open(str(sdist_file)) as tf:
            assert 'package1-0.1/pyproject.toml' in tf.getnames()


LIST_FILES = """\
#!{python}
import sys
from os.path import join
if '--deleted' not in sys.argv:
    files = [
        'foo',
        join('dir1', 'bar'),
        join('dir1', 'subdir', 'qux'),
        join('dir2', 'abc'),
        join('dist', 'def'),
    ]
    mode = '{vcs}'
    if mode == 'git':
        print('\\0'.join(files), end='\\0')
    elif mode == 'hg':
        for f in files:
            print(f)
"""

LIST_FILES_GIT = LIST_FILES.format(python=sys.executable, vcs='git')
LIST_FILES_HG = LIST_FILES.format(python=sys.executable, vcs='hg')


def test_get_files_list_git(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()

    builder = sdist.SdistBuilder.from_ini_path(td / 'pyproject.toml')
    with MockCommand('git', LIST_FILES_GIT):
        with patch('flit.vcs.git_validate_ignore', return_value=True):
            files = builder.select_files()

    assert set(files) == {
        'foo', pjoin('dir1', 'bar'), pjoin('dir1', 'subdir', 'qux'),
        pjoin('dir2', 'abc')
    }

def test_get_files_list_hg(tmp_path):
    dir1 = tmp_path / 'dir1'
    copytree(str(samples_dir / 'module1_toml'), str(dir1))
    (tmp_path / '.hg').mkdir()
    builder = sdist.SdistBuilder.from_ini_path(dir1 / 'pyproject.toml')
    with MockCommand('hg', LIST_FILES_HG):
        files = builder.select_files()

    assert set(files) == {
        'bar', pjoin('subdir', 'qux')
    }

def test_make_stubs_pkg():
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'sample-stubs' / 'pyproject.toml')
    with TemporaryDirectory() as td:
        td = Path(td)
        builder.build(td)
        sdist_file = td / 'wcwidth_stubs-0.2.13.1.tar.gz'
        assert_isfile(sdist_file)
