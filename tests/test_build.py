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
import sys
from os.path import join
if '--deleted' not in sys.argv:
    files = ['pyproject.toml', '{module}', 'EG_README.rst']
    print('\\0'.join(files), end='\\0')
"""

def test_build_main(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()   # Fake a git repo

    with MockCommand('git', LIST_FILES_TEMPLATE.format(
            python=sys.executable, module='module1.py')):
        res = build.main(td / 'pyproject.toml')
    assert res.wheel.file.suffix == '.whl'
    assert res.sdist.file.name.endswith('.tar.gz')

    assert_isdir(td / 'dist')

def test_build_sdist_only(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()  # Fake a git repo

    with MockCommand('git', LIST_FILES_TEMPLATE.format(
            python=sys.executable, module='module1.py')):
        res = build.main(td / 'pyproject.toml', formats={'sdist'})
    assert res.wheel is None

    # Compare str path to work around pathlib/pathlib2 mismatch on Py 3.5
    assert [str(p) for p in (td / 'dist').iterdir()] == [str(res.sdist.file)]

def test_build_wheel_only(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()  # Fake a git repo

    with MockCommand('git', LIST_FILES_TEMPLATE.format(
            python=sys.executable, module='module1.py')):
        res = build.main(td / 'pyproject.toml', formats={'wheel'})
    assert res.sdist is None

    # Compare str path to work around pathlib/pathlib2 mismatch on Py 3.5
    assert [str(p) for p in (td / 'dist').iterdir()] == [str(res.wheel.file)]

def test_build_module_no_docstring():
    with TemporaryDirectory() as td:
        pyproject = Path(td, 'pyproject.toml')
        shutil.copy(str(samples_dir / 'no_docstring-pkg.toml'), str(pyproject))
        shutil.copy(str(samples_dir / 'no_docstring.py'), td)
        shutil.copy(str(samples_dir / 'EG_README.rst'), td)
        Path(td, '.git').mkdir()   # Fake a git repo


        with MockCommand('git', LIST_FILES_TEMPLATE.format(
                python=sys.executable, module='no_docstring.py')):
            with pytest.raises(common.NoDocstringError) as exc_info:
                build.main(pyproject)
            assert 'no_docstring.py' in str(exc_info.value)
