import pathlib

import pytest

from flit.inifile import read_pkg_ini, ConfigError

samples_dir = pathlib.Path(__file__).parent / 'samples'

def test_invalid_classifier():
    with pytest.raises(ConfigError):
        read_pkg_ini(samples_dir / 'invalid_classifier.ini')

def test_missing_entrypoints():
    with pytest.raises(FileNotFoundError):
        read_pkg_ini(samples_dir / 'entrypoints_missing.ini')

def test_misspelled_key():
    with pytest.raises(ConfigError) as e_info:
        read_pkg_ini(samples_dir / 'misspelled-key.ini')

    assert 'description-file' in str(e_info)

def test_description_file():
    info = read_pkg_ini(samples_dir / 'package1-pkg.ini')
    assert info['metadata']['description'] == \
        "Sample description for test.\n"
