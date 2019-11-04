from pathlib import Path
import pytest

from flit.inifile import read_flit_config, ConfigError

samples_dir = Path(__file__).parent / 'samples'

def test_invalid_classifier():
    with pytest.raises(ConfigError):
        read_flit_config(samples_dir / 'invalid_classifier.ini')

def test_classifiers_with_space():
    """
    Check that any empty lines (including the first one) for
    classifiers are stripped
    """
    read_flit_config(samples_dir / 'classifiers_with_space.ini')
