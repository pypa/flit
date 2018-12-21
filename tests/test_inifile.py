import logging
import re
from pathlib import Path

import pytest

from flit.inifile import read_pkg_ini, ConfigError, flatten_entrypoints, _prep_metadata

samples_dir = Path(__file__).parent / 'samples'

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

def test_missing_description_file():
    with pytest.raises(ConfigError, match=r"Description file .* does not exist"):
        read_pkg_ini(samples_dir / 'missing-description-file.toml')
    assert re.search(r"Description file .* does not exist", str(error))

def test_bad_description_extension(caplog):
    info = read_pkg_ini(samples_dir / 'bad-description-ext.toml')
    assert info['metadata']['description_content_type'] is None
    assert any((r.levelno == logging.WARN and "Unknown extension" in r.msg)
                for r in caplog.records)

def test_extras():
    info = read_pkg_ini(samples_dir / 'extras.toml')
    requires_dist = set(info['metadata']['requires_dist'])
    assert requires_dist == {
        'toml',
        'pytest; extra == "test"',
        'requests; extra == "custom"',
    }

def test_extras_dev_conflict():
    with pytest.raises(ValueError, match=r'Ambiguity'):
        read_pkg_ini(samples_dir / 'extras-dev-conflict.toml')

def test_extras_dev_warning(caplog):
    info = read_pkg_ini(samples_dir / 'requires-dev.toml')
    assert '“dev-requires = ...” is obsolete' in caplog.text
    assert set(info['metadata']['requires_dist']) == {'apackage; extra == "dev"'}

def test_requires_extra_env_marker():
    info = read_pkg_ini(samples_dir / 'requires-extra-envmark.toml')
    assert info['metadata']['requires_dist'][0].startswith('pathlib2;')

@pytest.mark.parametrize(('erroneous', 'match'), [
    ({'requires-extra': None}, r'Expected a dict for requires-extra field'),
    ({'requires-extra': dict(dev=None)}, r'Expected a dict of lists for requires-extra field'),
    ({'requires-extra': dict(dev=[1])}, r'Expected a string list for requires-extra'),
])
def test_faulty_requires_extra(erroneous, match):
    metadata = {'module': 'mymod', 'author': '', 'author-email': ''}
    with pytest.raises(ConfigError, match=match):
        _prep_metadata(dict(metadata, **erroneous), None)
