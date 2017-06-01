from contextlib import contextmanager
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from flit import vcs

@contextmanager
def cwd(path):
    if isinstance(path, Path):
        path = str(path)
    old_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_wd)

def test_identify_git_parent():
    with TemporaryDirectory() as td:
        td = Path(td)
        (td / '.git').mkdir()
        subdir = (td / 'subdir')
        subdir.mkdir()
        with cwd(subdir):
            assert vcs.identify_vcs(Path('.')).name == 'git'

