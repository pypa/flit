from pathlib import Path

from testpath import assert_isfile

from flit_core.wheel import make_wheel_in

samples_dir = Path(__file__).parent / 'samples'

def test_licenses_dir(tmp_path):
    # Smoketest for https://github.com/takluyver/flit/issues/399
    info = make_wheel_in(samples_dir / 'inclusion' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
