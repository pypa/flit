import logging
from pathlib import Path
import pytest

from flit_core import config

samples_dir = Path(__file__).parent / 'samples'

def test_flatten_entrypoints():
    r = config.flatten_entrypoints({'a': {'b': {'c': 'd'}, 'e': {'f': {'g': 'h'}}, 'i': 'j'}})
    assert r == {'a': {'i': 'j'}, 'a.b': {'c': 'd'}, 'a.e.f': {'g': 'h'}}

def test_load_toml():
    inf = config.read_flit_config(samples_dir / 'module1-pkg.toml')
    assert inf.module == 'module1'
    assert inf.metadata['home_page'] == 'http://github.com/sirrobin/module1'

def test_misspelled_key():
    with pytest.raises(config.ConfigError) as e_info:
        config.read_flit_config(samples_dir / 'misspelled-key.toml')

    assert 'description-file' in str(e_info.value)

def test_description_file():
    info = config.read_flit_config(samples_dir / 'package1.toml')
    assert info.metadata['description'] == \
        "Sample description for test.\n"
    assert info.metadata['description_content_type'] == 'text/x-rst'

def test_missing_description_file():
    with pytest.raises(config.ConfigError, match=r"Description file .* does not exist"):
        config.read_flit_config(samples_dir / 'missing-description-file.toml')

def test_bad_description_extension(caplog):
    info = config.read_flit_config(samples_dir / 'bad-description-ext.toml')
    assert info.metadata['description_content_type'] is None
    assert any((r.levelno == logging.WARN and "Unknown extension" in r.msg)
                for r in caplog.records)

def test_extras():
    info = config.read_flit_config(samples_dir / 'extras.toml')
    requires_dist = set(info.metadata['requires_dist'])
    assert requires_dist == {
        'toml',
        'pytest ; extra == "test"',
        'requests ; extra == "custom"',
    }
    assert set(info.metadata['provides_extra']) == {'test', 'custom'}

def test_extras_dev_conflict():
    with pytest.raises(config.ConfigError, match=r'dev-requires'):
        config.read_flit_config(samples_dir / 'extras-dev-conflict.toml')

def test_extras_dev_warning(caplog):
    info = config.read_flit_config(samples_dir / 'requires-dev.toml')
    assert '"dev-requires = ..." is obsolete' in caplog.text
    assert set(info.metadata['requires_dist']) == {'apackage ; extra == "dev"'}

def test_requires_extra_env_marker():
    info = config.read_flit_config(samples_dir / 'requires-extra-envmark.toml')
    assert info.metadata['requires_dist'][0].startswith('pathlib2 ;')

@pytest.mark.parametrize(('erroneous', 'match'), [
    ({'requires-extra': None}, r'Expected a dict for requires-extra field'),
    ({'requires-extra': dict(dev=None)}, r'Expected a dict of lists for requires-extra field'),
    ({'requires-extra': dict(dev=[1])}, r'Expected a string list for requires-extra'),
])
def test_faulty_requires_extra(erroneous, match):
    metadata = {'module': 'mymod', 'author': '', 'author-email': ''}
    with pytest.raises(config.ConfigError, match=match):
        config._prep_metadata(dict(metadata, **erroneous), None)

@pytest.mark.parametrize(('path', 'err_match'), [
    ('../bar', 'out of the directory'),
    ('foo/../../bar', 'out of the directory'),
    ('/home', 'absolute path'),
    ('foo:bar', 'bad character'),
    ('foo/**/bar', '[Rr]ecursive glob')
])
def test_bad_include_paths(path, err_match):
    toml_cfg = {'tool': {'flit': {
        'metadata': {'module': 'xyz', 'author': 'nobody'},
        'sdist': {'include': [path]}
    }}}

    with pytest.raises(config.ConfigError, match=err_match):
        config.prep_toml_config(toml_cfg, None)
