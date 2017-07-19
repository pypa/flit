import builtins
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from flit import init

def test_store_defaults():
    with TemporaryDirectory() as td:
        with patch.object(init, 'get_data_dir', lambda : Path(td)):
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
