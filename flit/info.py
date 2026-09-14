"""
This module contains code for the "info" subcommand
"""


def get_version(ini_path):
    # type: (str) -> str
    """
    This will return the package version as a string.

    :param ini_path: The filename of the main config-file
        (flit.ini/pyproject.toml)
    """
    from . import inifile
    from .common import Module, make_metadata
    ini_info = inifile.read_pkg_ini(ini_path)
    module = Module(ini_info['module'], ini_path.parent)
    metadata = make_metadata(module, ini_info)
    output = metadata.version
    return output
