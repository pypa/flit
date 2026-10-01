import ast
from os.path import join as pjoin
from pathlib import Path
import pytest
from shutil import which, copytree
from subprocess import run
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
        files = builder.select_files()

    assert set(files) == {
        'foo', pjoin('dir1', 'bar'), pjoin('dir1', 'subdir', 'qux'),
        pjoin('dir2', 'abc')
    }

def test_get_files_list_with_real_git(copy_sample):
    if not which('git'):
        pytest.skip("requires git")

    td = copy_sample('module1_toml')
    unicode_file = td / 'café.txt'
    unicode_file.write_text('tracked by git', encoding='utf-8')

    run(['git', 'init'], cwd=td, check=True, capture_output=True)
    run(['git', 'add', '.'], cwd=td, check=True, capture_output=True)

    builder = sdist.SdistBuilder.from_ini_path(td / 'pyproject.toml')
    files = builder.select_files()

    assert unicode_file.name in files

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


def _make_builder(tmp_path, include):
    """Build an SdistBuilder over tmp_path with the given sdist include list."""
    (tmp_path / "mypkg").mkdir()
    (tmp_path / "mypkg" / "__init__.py").write_text('__version__ = "0.1"\n')
    (tmp_path / "EG_README.rst").write_text("readme\n")
    (tmp_path / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["flit_core >=3.2,<4"]\n'
        'build-backend = "flit_core.buildapi"\n\n'
        "[project]\n"
        'name = "mypkg"\n'
        'version = "0.1"\n'
        'description = "t"\n'
        'readme = "EG_README.rst"\n\n'
        "[tool.flit.sdist]\n"
        f"include = {include!r}\n"
    )
    return sdist.SdistBuilder.from_ini_path(tmp_path / "pyproject.toml")


# The files select_files() would report if the tree were under VCS.  Passing
# them in directly keeps these tests independent of git/hg.
BASE_FILES = ["pyproject.toml", "EG_README.rst", "mypkg/__init__.py"]


def test_apply_includes_follows_dir_symlink(tmp_path):
    """A symlinked directory inside an included dir is walked (see #509)."""
    (tmp_path / "real_data").mkdir()
    (tmp_path / "real_data" / "data.txt").write_text("hello")
    (tmp_path / "docs").mkdir()
    try:
        (tmp_path / "docs" / "linked").symlink_to(
            tmp_path / "real_data", target_is_directory=True
        )
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")

    builder = _make_builder(tmp_path, ["docs/"])
    files = builder.apply_includes_excludes(list(BASE_FILES))
    assert "docs/linked/data.txt" in files


def test_apply_includes_dir_symlink_cycle_terminates(tmp_path):
    """A symlink cycle must not make the sdist walk loop forever (see #509)."""
    (tmp_path / "docs" / "sub").mkdir(parents=True)
    (tmp_path / "docs" / "sub" / "f.txt").write_text("x")
    try:
        (tmp_path / "docs" / "sub" / "loop").symlink_to(
            tmp_path / "docs", target_is_directory=True
        )
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")

    builder = _make_builder(tmp_path, ["docs/"])
    files = builder.apply_includes_excludes(list(BASE_FILES))
    assert "docs/sub/f.txt" in files
    # Each real file appears once, not once per cycle iteration.
    assert len(files) == len(set(files))
    assert len(files) < 20, f"walk did not terminate cleanly: {sorted(files)}"
