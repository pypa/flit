import configparser

def get_info_from_ini(target):
    cp = configparser.ConfigParser()
    with target.ini_file.open() as f:
        cp.read_file(f)
    return cp

script_template = """\
#!{interpreter}
from {module} import {func}
{func}()
"""

def parse_entry_point(ep: str):
    if ':' not in ep:
        raise ValueError("Invalid entry point (no ':'): %r" % ep)
    mod, func = ep.split(':')

    if not func.isidentifier():
        raise ValueError("Invalid entry point: %r is not an identifier" % func)
    for piece in mod.split('.'):
        if not piece.isidentifier():
            raise ValueError("Invalid entry point: %r is not a module path" % piece)

    return mod, func