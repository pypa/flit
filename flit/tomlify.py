"""Convert a flit.ini file to pyproject.toml
"""
import argparse
from collections import OrderedDict
import configparser
import os
from pathlib import Path
import tomli_w

from .config import metadata_list_fields


TEMPLATE = """\
[build-system]
requires = ["flit_core >=2,<4"]
build-backend = "flit_core.buildapi"

[tool.flit.metadata]
{metadata}
"""

class CaseSensitiveConfigParser(configparser.ConfigParser):
    optionxform = staticmethod(str)

def convert(path):
    cp = configparser.ConfigParser()
    with path.open(encoding='utf-8') as f:
        cp.read_file(f)

    ep_file = Path('entry_points.txt')
    metadata = OrderedDict()
    for name, value in cp['metadata'].items():
        if name in metadata_list_fields:
            metadata[name] = [l for l in value.splitlines() if l.strip()]
        elif name == 'entry-points-file':
            ep_file = Path(value)
        else:
            metadata[name] = value

    if 'scripts' in cp:
        scripts = OrderedDict(cp['scripts'])
    else:
        scripts = {}

    entrypoints = CaseSensitiveConfigParser()
    if ep_file.is_file():
        with ep_file.open(encoding='utf-8') as f:
            entrypoints.read_file(f)

    written_entrypoints = False
    with Path('pyproject.toml').open('w', encoding='utf-8') as f:
        f.write(TEMPLATE.format(metadata=tomli_w.dumps(metadata)))

        if scripts:
            f.write('\n[tool.flit.scripts]\n')
            f.write(tomli_w.dumps(scripts))

        for groupname, group in entrypoints.items():
            if not dict(group):
                continue

            if '.' in groupname:
                groupname = '"{}"'.format(groupname)
            f.write('\n[tool.flit.entrypoints.{}]\n'.format(groupname))
            f.write(tomli_w.dumps(OrderedDict(group)))
            written_entrypoints = True

    print("Written 'pyproject.toml'")
    files = str(path)
    if written_entrypoints:
        files += ' and ' + str(ep_file)
    print("Please check the new file, then remove", files)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--ini-file', type=Path, default='flit.ini')
    args = ap.parse_args(argv)

    os.chdir(str(args.ini_file.parent))
    convert(Path(args.ini_file.name))

if __name__ == '__main__':
    main()
