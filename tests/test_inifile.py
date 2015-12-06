import pathlib

import pytest

from flit.inifile import read_pkg_ini, ConfigError, modify_config

samples_dir = pathlib.Path(__file__).parent / 'samples'

def test_invalid_classifier():
    with pytest.raises(ConfigError):
        read_pkg_ini(samples_dir / 'invalid_classifier.ini')

def test_missing_entrypoints():
    with pytest.raises(FileNotFoundError):
        read_pkg_ini(samples_dir / 'entrypoints_missing.ini')

def test_ini_roundtrip_contextmanager():
    return
    ini_path = samples_dir / 'entrypoints_valid.ini'
    with ini_path.open() as f:
        expected = f.read()

    with modify_config(ini_path):
        pass

    with ini_path.open() as f:
        modified = f.read()

    pytest.assert_equal(expected, modified)




