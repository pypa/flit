import pytest

from flit.common import Metadata
from flit.inifile import read_pkg_ini

def test_extras(samples_dir):
    info = read_pkg_ini(samples_dir / 'extras.toml')
    assert info['metadata']['extras_require']['test'] == ['pytest']
    assert info['metadata']['extras_require']['custom'] == ['requests']

def test_extras_dev_conflict(samples_dir):
    info = read_pkg_ini(samples_dir / 'extras-dev-conflict.toml')
    with pytest.raises(ValueError, match=r'Ambiguity'):
        Metadata(dict(name=info['module'], version='0.0', summary='', **info['metadata']))

def test_extra_conditions(samples_dir):
    info = read_pkg_ini(samples_dir / 'extras.toml')
    meta = Metadata(dict(name=info['module'], version='0.0', summary='', **info['metadata']))
    assert set(meta.requires_dist) == {'toml', 'pytest; extra == "test"', 'requests; extra == "custom"'}
