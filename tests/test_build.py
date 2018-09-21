from pathlib import Path
import pytest
import shutil
import sys
from tempfile import TemporaryDirectory
from testpath import assert_isdir, MockCommand

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

def test_build_main():
    with TemporaryDirectory() as td:
        pyproject = Path(td, 'pyproject.toml')
        shutil.copy(str(samples_dir / 'module1-pkg.toml'), str(pyproject))
        shutil.copy(str(samples_dir / 'module1.py'), td)
        shutil.copy(str(samples_dir / 'EG_README.rst'), td)
        Path(td, '.git').mkdir()   # Fake a git repo

        with MockCommand('git', LIST_FILES_TEMPLATE.format(
                python=sys.executable, module='module1.py')):
            res = build.main(pyproject)
        assert res.wheel.file.suffix == '.whl'
        assert res.sdist.file.name.endswith('.tar.gz')

        assert_isdir(Path(td, 'dist'))


def test_build_module_no_docstring():
    with TemporaryDirectory() as td:
        pyproject = Path(td, 'pyproject.toml')
        shutil.copy(str(samples_dir / 'no_docstring-pkg.toml'), str(pyproject))
        shutil.copy(str(samples_dir / 'no_docstring.py'), td)
        shutil.copy(str(samples_dir / 'EG_README.rst'), td)
        Path(td, '.git').mkdir()   # Fake a git repo


        with MockCommand('git', LIST_FILES_TEMPLATE.format(
                python=sys.executable, module='no_docstring.py')):
            with pytest.raises(ValueError) as exc_info:
                build.main(pyproject)
            errmsg_head, errmsg_tail = str(exc_info.value).split('(')
            errmsg_head_shouldbe = ('Flit cannot package module without '
            'docstring, or empty docstring. Please add a docstring to your '
            'module ')
            errmsg_tail_shouldbe = str(Path(td, 'no_docstring.py')) + ').'
            assert errmsg_head == errmsg_head_shouldbe
            assert errmsg_tail == errmsg_tail_shouldbe
