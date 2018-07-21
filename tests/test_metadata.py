from pathlib import Path

import pytest

from flit.common import Metadata
from flit.inifile import read_pkg_ini

samples_dir = Path(__file__).parent / 'samples'

def test_extras():
    info = read_pkg_ini(samples_dir / 'extras.toml')
    assert info['metadata']['requires_extra']['test'] == ['pytest']
    assert info['metadata']['requires_extra']['custom'] == ['requests']

def test_extras_dev_conflict():
    info = read_pkg_ini(samples_dir / 'extras-dev-conflict.toml')
    with pytest.raises(ValueError, match=r'Ambiguity'):
        Metadata(dict(name=info['module'], version='0.0', summary='', **info['metadata']))

def test_extras_dev_warning(caplog):
    info = read_pkg_ini(samples_dir / 'extras-dev-conflict.toml')
    info['metadata']['requires_extra'] = {}
    meta = Metadata(dict(name=info['module'], version='0.0', summary='', **info['metadata']))
    assert '“dev-requires = ...” is obsolete' in caplog.text
    assert set(meta.requires_dist) == {'apackage; extra == "dev"'}

def test_extra_conditions():
    info = read_pkg_ini(samples_dir / 'extras.toml')
    meta = Metadata(dict(name=info['module'], version='0.0', summary='', **info['metadata']))
    assert set(meta.requires_dist) == {'toml', 'pytest; extra == "test"', 'requests; extra == "custom"'}
