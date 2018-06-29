import logging

import pytest

from flit.inifile import read_pkg_ini, ConfigError, flatten_entrypoints

def test_invalid_classifier(samples_dir):
    with pytest.raises(ConfigError):
        read_pkg_ini(samples_dir / 'invalid_classifier.ini')

def test_classifiers_with_space(samples_dir):
    """
    Check that any empty lines (including the first one) for
    classifiers are stripped
    """
    read_pkg_ini(samples_dir / 'classifiers_with_space.ini')

def test_requires_with_empty_lines(samples_dir):
    ini_info = read_pkg_ini(samples_dir / 'requires_with_empty_lines.ini')
    assert ini_info['metadata']['requires_dist'] == ['foo', 'bar']

def test_missing_entrypoints(samples_dir):
    with pytest.raises(FileNotFoundError):
        read_pkg_ini(samples_dir / 'entrypoints_missing.ini')

def test_flatten_entrypoints():
    r = flatten_entrypoints({'a': {'b': {'c':'d'}, 'e': {'f': {'g':'h'}}, 'i':'j'}})
    assert r == {'a': {'i': 'j'}, 'a.b': {'c': 'd'}, 'a.e.f': {'g': 'h'}}

def test_load_toml(samples_dir):
    inf = read_pkg_ini(samples_dir / 'module1-pkg.toml')
    assert inf['module'] == 'module1'
    assert inf['metadata']['home_page'] == 'http://github.com/sirrobin/module1'

def test_misspelled_key(samples_dir):
    with pytest.raises(ConfigError) as e_info:
        read_pkg_ini(samples_dir / 'misspelled-key.ini')

    assert 'description-file' in str(e_info)

def test_description_file(samples_dir):
    info = read_pkg_ini(samples_dir / 'package1-pkg.ini')
    assert info['metadata']['description'] == \
        "Sample description for test.\n"
    assert info['metadata']['description_content_type'] == 'text/x-rst'

def test_bad_description_extension(caplog, samples_dir):
    info = read_pkg_ini(samples_dir / 'bad-description-ext.toml')
    assert info['metadata']['description_content_type'] is None
    assert any((r.levelno == logging.WARN and "Unknown extension" in r.msg)
                for r in caplog.records)
