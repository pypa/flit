import pathlib

import pytest

from flit.inifile import read_pkg_ini, ConfigError, flatten_entrypoints

samples_dir = pathlib.Path(__file__).parent / 'samples'

def test_invalid_classifier():
    with pytest.raises(ConfigError):
        read_pkg_ini(samples_dir / 'invalid_classifier.ini')

def test_missing_entrypoints():
    with pytest.raises(FileNotFoundError):
        read_pkg_ini(samples_dir / 'entrypoints_missing.ini')

def test_flatten_entrypoints():
    r = flatten_entrypoints({'a': {'b': {'c':'d'}, 'e': {'f': {'g':'h'}}, 'i':'j'}})
    assert r == {'a': {'i': 'j'}, 'a.b': {'c': 'd'}, 'a.e.f': {'g': 'h'}}

def test_load_toml():
    inf = read_pkg_ini(samples_dir / 'module1-pkg.toml')
    assert inf['module'] == 'module1'
    assert inf['metadata']['home_page'] == 'http://github.com/sirrobin/module1'
