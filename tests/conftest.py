from pathlib import Path
import pytest
from shutil import copytree

samples_dir = Path(__file__).parent / 'samples'

@pytest.fixture
def copy_sample(tmp_path):
    """Copy a subdirectory from the samples dir to a temp dir"""
    def copy(dirname):
        dst = tmp_path / dirname
        copytree(str(samples_dir / dirname), str(dst))
        return dst

    return copy
