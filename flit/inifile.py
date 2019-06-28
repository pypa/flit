import os

from flit_core.inifile import *
from flit_core.inifile import read_pkg_ini as _read_pkg_ini_core
from .validate import validate_config

def read_pkg_ini(path):
    """Read and check the `pyproject.toml` or `flit.ini` file with data about the package.
    """
    res = _read_pkg_ini_core(str(path))

    if validate_config(res):
        if os.environ.get('FLIT_ALLOW_INVALID'):
            log.warning("Allowing invalid data (FLIT_ALLOW_INVALID set). Uploads may still fail.")
        else:
            raise ConfigError("Invalid config values (see log)")
    return res
