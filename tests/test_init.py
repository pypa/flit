from pathlib import Path
from tempfile import TemporaryDirectory
from testpath import assert_isfile

from flit import init

def test_write_license():
    with TemporaryDirectory() as td:
        initer = init.IniterBase(td)
        initer.write_license('mit', 'Sir Robin')
        assert_isfile(Path(td, 'LICENSE'))

def test_guess_module_name():
    with TemporaryDirectory() as td:
        td = Path(td)
        (td / 'setup.py').touch()
        (td / 'tests').mkdir()
        (td / 'tests' / '__init__.py').touch()
        (td / 'caerbannog').mkdir()
        (td / 'caerbannog' / '__init__.py').touch()
        initer = init.IniterBase(td)
        assert initer.guess_module_name() == 'caerbannog'
