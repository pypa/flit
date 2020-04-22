from pathlib import Path
import pytest

from flit.config import read_flit_config, ConfigError

samples_dir = Path(__file__).parent / 'samples'

def test_invalid_classifier():
    with pytest.raises(ConfigError):
        read_flit_config(samples_dir / 'invalid_classifier.toml')
