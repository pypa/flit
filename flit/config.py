import os

from flit_core.config import *
from flit_core.config import read_flit_config as _read_flit_config_core
from .validate import validate_config


def read_flit_config(path):
    """Read and check the `pyproject.toml` or `flit.ini` file with data about the package.
    """
    res = _read_flit_config_core(path)

    if validate_config(res):
        if os.environ.get('FLIT_ALLOW_INVALID'):
            log.warning("Allowing invalid data (FLIT_ALLOW_INVALID set). Uploads may still fail.")
        else:
            raise ConfigError("Invalid config values (see log)")
    return res
