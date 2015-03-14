"""A simple packaging tool for simple packages."""
import argparse
import hashlib
import logging
import os
import pathlib
import shutil
import sys
from importlib.machinery import SourceFileLoader
import zipfile

from . import common

__version__ = '0.1'

log = logging.getLogger(__name__)

def get_info_from_module(target):
    sl = SourceFileLoader(target.name, str(target.file))
    m = sl.load_module()
    docstring_lines = m.__doc__.splitlines()
    return {'description': docstring_lines[0],
            'long_description': '\n'.join(docstring_lines[1:]),
            'version': m.__version__}

wheel_file_template = """\
Wheel-Version: 1.0
Generator: flit {version}
Root-Is-Purelib: true
""".format(version=__version__)

def wheel(target, upload=False):
    build_dir = target.path.parent / 'build' / 'flit'
    try:
        build_dir.mkdir(parents=True)
    except FileExistsError:
        shutil.rmtree(str(build_dir))
        build_dir.mkdir()

    # Copy module/package to build directory
    if target.is_package:
        ignore = shutil.ignore_patterns('*.pyc', '__pycache__', 'pypi.ini')
        shutil.copytree(str(target.path), str(build_dir / target.name), ignore=ignore)
    else:
        shutil.copy2(str(target.path), str(build_dir))

    module_info = get_info_from_module(target)
    ini_info = common.get_info_from_ini(target)
    dist_version = target.name + '-' + module_info['version']
    py2_support = ini_info.getboolean('package', 'python2', fallback=False)

    data_dir = build_dir / (dist_version + '.data')

    # Write scripts
    if ini_info.has_section('scripts'):
        (data_dir / 'scripts').mkdir(parents=True)
        for name, entrypt in ini_info['scripts'].items():
            module, func = common.parse_entry_point(entrypt)
            script_file = (data_dir / 'scripts' / name)
            log.debug('Writing script to %s', script_file)
            script_file.touch(0o755, exist_ok=False)
            with script_file.open('w') as f:
                f.write(common.script_template.format(
                    interpreter='python',
                    module=module,
                    func=func
                ))

    dist_info = build_dir / (dist_version + '.dist-info')
    dist_info.mkdir()

    with (dist_info / 'WHEEL').open('w') as f:
        f.write(wheel_file_template)
        if py2_support:
            f.write("Tag: py2-none-any\n")
        f.write("Tag: py3-none-any\n")

    pkg_config = ini_info['package']
    metadata = [
        ('Metadata-Version', '1.2'),
        ('Name', target.name),
        ('Version', module_info['version']),
        ('Summary', module_info['description']),
        ('Home-page', pkg_config['url']),
        ('License', ini_info.get('package', 'license', fallback='UNKNOWN')),
        ('Platform', ini_info.get('package', 'platform', fallback='UNKNOWN')),
    ]
    optional_fields = [
        ('Keywords', 'keywords'),
        ('Author', 'author'),
        ('Author-email', 'author-email'),
        ('Maintainer', 'maintainer'),
        ('Maintainer-email', 'maintainer-email'),
        ('License', 'license'),
    ]
    for dst, src in optional_fields:
        if src in pkg_config:
            metadata.append((dst, pkg_config[src]))
    for clsfr in ini_info.get('package', 'classifiers', fallback='').splitlines():
        metadata.append(('Classifier', clsfr))
    for req in ini_info.get('package', 'requirements', fallback='').splitlines():
        metadata.append(('Requires-Dist', req))


    with (dist_info / 'METADATA').open('w') as f:
        for field, value in metadata:
            f.write("{}: {}\n".format(field, value))
        if module_info['long_description']:
            f.write('\n' + module_info['long_description'] + '\n')

    records = []
    for dirpath, dirs, files in os.walk(str(build_dir)):
        reldir = os.path.relpath(dirpath, str(build_dir))
        for f in files:
            relfile = os.path.join(reldir, f)
            file = os.path.join(dirpath, f)
            h = hashlib.sha256()
            with open(file, 'rb') as fp:
                h.update(fp.read())
            size = os.stat(file).st_size
            records.append((relfile, h.hexdigest(), size))

    with (dist_info / 'RECORD').open('w') as f:
        for path, hash, size in records:
            f.write('{},sha256={},{}\n'.format(path, hash, size))
        # RECORD itself is recorded with no hash or size
        f.write(dist_version + '.dist-info/RECORD,,\n')

    dist_dir = target.path.parent / 'dist'
    try:
        dist_dir.mkdir()
    except FileExistsError:
        pass
    tag = ('py2.' if py2_support else '') + 'py3-none-any'
    filename = '{}-{}.whl'.format(dist_version, tag)
    with zipfile.ZipFile(str(dist_dir / filename), 'w',
                         compression=zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirs, files in os.walk(str(build_dir)):
            reldir = os.path.relpath(dirpath, str(build_dir))
            for file in files:
                z.write(os.path.join(dirpath, file), os.path.join(reldir, file))

    log.info("Created %s", dist_dir / filename)

class Importable(object):
    def __init__(self, path):
        self.path = pathlib.Path(path)

    @property
    def name(self):
        n = self.path.name
        if n.endswith('.py'):
            n = n[:-3]
        return n

    @property
    def file(self):
        if self.is_package:
            return self.path / '__init__.py'
        else:
            return self.path

    @property
    def is_package(self):
        return self.path.is_dir()

    @property
    def ini_file(self):
        if self.is_package:
            return self.path / 'pypi.ini'
        else:
            return self.path.with_name(self.name + '-pypi.ini')

    def check(self):
        if not self.file.is_file():
            raise FileNotFoundError(self.path)
        if not self.name.isidentifier():
            raise ValueError("{} is not a valid package name".format(self.name))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('package',
        help="Path to the Python package/module to package",
    )
    subparsers = ap.add_subparsers(title='subcommands', dest='subcmd')

    parser_wheel = subparsers.add_parser('wheel')
    parser_wheel.add_argument('--upload', action='store', nargs='?',
                              const='pypi', default=None)

    parser_install = subparsers.add_parser('install')
    parser_install.add_argument('--symlink', action='store_true')

    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    pkg = Importable(args.package)
    pkg.check()

    if args.subcmd == 'wheel':
        wheel(pkg, upload=args.upload)
    elif args.subcmd == 'install':
        from .install import install
        install(pkg, symlink=args.symlink)
    else:
        sys.exit('No command specified')

if __name__ == '__main__':
    main()