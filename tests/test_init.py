import builtins
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from testpath import assert_isfile
from unittest.mock import patch

from flit import init


@contextmanager
def patch_data_dir():
    with TemporaryDirectory() as td:
        with patch.object(init, 'get_data_dir', lambda: Path(td)):
            yield td

def test_store_defaults():
    with patch_data_dir():
        assert init.get_defaults() == {}
        d = {'author': 'Test'}
        init.store_defaults(d)
        assert init.get_defaults() == d

def fake_input(entries):
    it = iter(entries)
    def inner(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return inner

def faking_input(entries):
    return patch.object(builtins, 'input', fake_input(entries))

def test_prompt_options():
    ti = init.TerminalIniter()
    with faking_input(['4', '1']):
        res = ti.prompt_options('Pick one', [('A', 'Apple'), ('B', 'Banana')])
    assert res == 'A'

    # Test with a default
    with faking_input(['']):
        res = ti.prompt_options('Pick one', [('A', 'Apple'), ('B', 'Banana')],
                                default='B')
    assert res == 'B'

@contextmanager
def make_dir(files=(), dirs=()):
    with TemporaryDirectory() as td:
        tdp = Path(td)
        for d in dirs:
            (tdp / d).mkdir()
        for f in files:
            (tdp / f).touch()
        yield td

def test_guess_module_name():
    with make_dir(['foo.py', 'foo-bar.py', 'test_foo.py', 'setup.py']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() == 'foo'

    with make_dir(['baz/__init__.py', 'tests/__init__.py'], ['baz', 'tests']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() == 'baz'

    with make_dir(['foo.py', 'bar.py']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() is None

def test_write_license():
    with TemporaryDirectory() as td:
        ib = init.IniterBase(td)
        ib.write_license('mit', 'Thomas Kluyver')
        assert_isfile(Path(td, 'LICENSE'))

def test_init():
    responses = ['foo', # Module name
                 'Thomas Kluyver',      # Author
                 'thomas@example.com',  # Author email
                 'http://example.com/', # Home page
                 '1'    # License (1 -> MIT)
                ]
    with TemporaryDirectory() as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()
        assert_isfile('flit.ini')
        assert_isfile('LICENSE')
