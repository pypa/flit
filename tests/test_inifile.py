import logging
import pathlib

import pytest

from flit.inifile import read_pkg_ini, ConfigError, flatten_entrypoints

samples_dir = pathlib.Path(__file__).parent / 'samples'

def test_invalid_classifier():
    with pytest.raises(ConfigError):
        read_pkg_ini(samples_dir / 'invalid_classifier.ini')

def test_classifiers_with_space():
    """
    Check that any empty lines (including the first one) for
    classifiers are stripped
    """
    read_pkg_ini(samples_dir / 'classifiers_with_space.ini')

def test_requires_with_empty_lines():
    ini_info = read_pkg_ini(samples_dir / 'requires_with_empty_lines.ini')
    assert ini_info['metadata']['requires_dist'] == ['foo', 'bar']

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

def test_misspelled_key():
    with pytest.raises(ConfigError) as e_info:
        read_pkg_ini(samples_dir / 'misspelled-key.ini')

    assert 'description-file' in str(e_info)

def test_description_file():
    info = read_pkg_ini(samples_dir / 'package1-pkg.ini')
    assert info['metadata']['description'] == \
        "Sample description for test.\n"
    assert info['metadata']['description_content_type'] == 'text/x-rst'

def test_bad_description_extension(caplog):
    info = read_pkg_ini(samples_dir / 'bad-description-ext.toml')
    assert info['metadata']['description_content_type'] is None
    assert any((r.levelno == logging.WARN and "Unknown extension" in r.msg)
                for r in caplog.records)
