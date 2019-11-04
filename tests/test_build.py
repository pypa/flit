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
    print('pyproject.toml')
    print('{module}')
    print('EG_README.rst')
"""

def test_build_main(copy_sample):
    td = copy_sample('module1_toml')
    shutil.copy(str(samples_dir / 'EG_README.rst'), str(td))
    (td / '.git').mkdir()   # Fake a git repo

    with MockCommand('git', LIST_FILES_TEMPLATE.format(
            python=sys.executable, module='module1.py')):
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


        with MockCommand('git', LIST_FILES_TEMPLATE.format(
                python=sys.executable, module='no_docstring.py')):
            with pytest.raises(common.NoDocstringError) as exc_info:
                build.main(pyproject)
            assert 'no_docstring.py' in str(exc_info.value)
