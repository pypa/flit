from pathlib import Path
import pytest
import shutil
import sys
from tempfile import TemporaryDirectory
from testpath import assert_isdir, MockCommand

from flit_core import common
from flit import build

samples_dir = Path(__file__).parent / 'samples'

LIST_FILES_TEMPLATE = """\
#!{python}
import sys, posixpath
tracked = {tracked}
untracked_deleted = {untracked_deleted}

if '--deleted' in sys.argv:
    files = untracked_deleted
else:
    files = tracked

for filename in map(posixpath.normpath, files):
    print(filename, end="\\0")
"""

MODULE1_TOML_FILES = ["EG_README.rst", "module1.py", "pyproject.toml"]

def make_git_script(
    tracked = MODULE1_TOML_FILES,
    untracked_deleted = ["dist/module1-0.1.tar.gz"]
):
    return LIST_FILES_TEMPLATE.format(
        python=sys.executable,
        tracked=tracked,
        untracked_deleted=untracked_deleted,
    )

def test_build_main(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()   # Fake a git repo

    with MockCommand('git', make_git_script()):
        res = build.main(td / 'pyproject.toml')
    assert res.wheel.file.suffix == '.whl'
    assert res.sdist.file.name.endswith('.tar.gz')

    assert_isdir(td / 'dist')

def test_build_sdist_only(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()  # Fake a git repo

    with MockCommand('git', make_git_script()):
        res = build.main(td / 'pyproject.toml', formats={'sdist'})
    assert res.wheel is None

    # Compare str path to work around pathlib/pathlib2 mismatch on Py 3.5
    assert [str(p) for p in (td / 'dist').iterdir()] == [str(res.sdist.file)]

def test_build_wheel_only(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()  # Fake a git repo

    with MockCommand('git', make_git_script()):
        res = build.main(td / 'pyproject.toml', formats={'wheel'})
    assert res.sdist is None

    # Compare str path to work around pathlib/pathlib2 mismatch on Py 3.5
    assert [str(p) for p in (td / 'dist').iterdir()] == [str(res.wheel.file)]

def test_build_ns_main(copy_sample):
    td = copy_sample('ns1-pkg')
    (td / '.git').mkdir()   # Fake a git repo
    tracked = [
        'EG_README.rst',
        'ns1/pkg/__init__.py',
        'pyproject.toml',
    ]
    untracked_deleted = ['dist/ns1.pkg-0.1.tar.gz']

    with MockCommand('git', make_git_script(tracked=tracked,
            untracked_deleted=untracked_deleted)):
        res = build.main(td / 'pyproject.toml')
    assert res.wheel.file.suffix == '.whl'
    assert res.sdist.file.name.endswith('.tar.gz')

    assert_isdir(td / 'dist')


def test_build_module_no_docstring():
    with TemporaryDirectory() as td:
        pyproject = Path(td, 'pyproject.toml')
        shutil.copy(str(samples_dir / 'no_docstring-pkg.toml'), str(pyproject))
        shutil.copy(str(samples_dir / 'no_docstring.py'), td)
        shutil.copy(str(samples_dir / 'EG_README.rst'), td)
        Path(td, '.git').mkdir()   # Fake a git repo
        tracked = [
            "pyproject.toml",
            "no_docstring.py",
            "EG_README.rst",
        ]

        with MockCommand('git', make_git_script(tracked=tracked)):
            with pytest.raises(common.NoDocstringError) as exc_info:
                build.main(pyproject)
            assert 'no_docstring.py' in str(exc_info.value)

def test_rebuild(copy_sample):
    """
    build artifacts should not cause subsequent builds to fail if no other
    files were changed
    """
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()   # Fake a git repo

    with MockCommand('git', make_git_script()):
        res = build.main(td / 'pyproject.toml')
        res = build.main(td / 'pyproject.toml')
