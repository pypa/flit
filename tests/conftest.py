from pathlib import Path

import pytest

SAMPLES_DIR = Path(__file__).parent / 'samples'

@pytest.fixture
def samples_dir(request):
    if request.cls:
        request.cls.samples_dir = SAMPLES_DIR
    return SAMPLES_DIR
