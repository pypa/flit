from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from testpath import assert_isdir, MockCommand

from flit import build

LIST_FILES = """\
#!{python}
import sys
from os.path import join
if '--deleted' not in sys.argv:
    print('pyproject.toml')
    print('module1.py')
    print('EG_README.rst')
""".format(python=sys.executable)

def test_build_main(samples_dir):
    with TemporaryDirectory() as td:
        pyproject = Path(td, 'pyproject.toml')
        shutil.copy(str(samples_dir / 'module1-pkg.toml'), str(pyproject))
        shutil.copy(str(samples_dir / 'module1.py'), td)
        shutil.copy(str(samples_dir / 'EG_README.rst'), td)
        Path(td, '.git').mkdir()   # Fake a git repo

        with MockCommand('git', LIST_FILES):
            res = build.main(pyproject)
        assert res.wheel.file.suffix == '.whl'
        assert res.sdist.file.name.endswith('.tar.gz')

        assert_isdir(Path(td, 'dist'))
