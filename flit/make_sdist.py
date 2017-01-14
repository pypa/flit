from collections import defaultdict
import io
import os
from pathlib import Path
from posixpath import join as pjoin
from pprint import pformat
import tarfile

from flit import common, inifile

SETUP = """\
#!/usr/bin/env python

from distutils.core import setup

{before}
setup(name={name!r},
      version={version!r},
      description={description!r},
      author={author!r},
      author_email={author_email!r},
      url={url!r},
      {extra}
     )
"""

PKG_INFO = """\
Metadata-Version: 1.1
Name: {name}
Version: {version}
Summary: {summary}
Home-page: {home_page}
Author: {author}
Author-email: {author_email}
"""

def exclude_pycache(tarinfo):
    if ('/__pycache__' in tarinfo.name) or tarinfo.name.endswith('.pyc'):
        return None
    return tarinfo

def auto_packages(pkgdir: str):
    """Discover subpackages and package_data"""
    pkgdir = os.path.normpath(pkgdir)
    pkg_name = os.path.basename(pkgdir)
    pkg_data = defaultdict(list)
    # Undocumented distutils feature: the empty string matches all package names
    pkg_data[''].append('*')
    packages = [pkg_name]
    subpkg_paths = set()

    def find_nearest_pkg(rel_path):
        parts = rel_path.split(os.sep)
        for i in reversed(range(1, len(parts))):
            ancestor = os.sep.join(parts[:i])
            if ancestor in subpkg_paths:
                pkg = '.'.join([pkg_name] + parts[:i])
                return pkg, os.sep.join(parts[i:])

        # Relative to the top-level package
        return pkg_name, rel_path

    for path, dirnames, filenames in os.walk(pkgdir, topdown=True):
        if os.path.basename(path) == '__pycache__':
            continue

        from_top_level = os.path.relpath(path, pkgdir)
        if from_top_level == '.':
            continue

        is_subpkg = '__init__.py' in filenames
        if is_subpkg:
            subpkg_paths.add(from_top_level)
            parts = from_top_level.split(os.sep)
            packages.append('.'.join([pkg_name] + parts))
        else:
            pkg, from_nearest_pkg = find_nearest_pkg(from_top_level)
            pkg_data[pkg].append(os.path.join(from_nearest_pkg, '*'))

    return packages, dict(pkg_data)


def make_sdist(ini_path=Path('flit.ini')):
    ini_info = inifile.read_pkg_ini(ini_path)
    module = common.Module(ini_info['module'], ini_path.parent)
    metadata = common.make_metadata(module, ini_info)

    target = ini_path.parent / 'dist' / '{}-{}.tar.gz'.format(metadata.name,
                                                              metadata.version)
    tf = tarfile.open(str(target), mode='w:gz')
    tf_dir = '{}-{}'.format(metadata.name, metadata.version)

    srcdir = str(ini_path.parent)

    def add_if_exists(name):
        src_path = pjoin(srcdir, name)
        dst_path = pjoin(tf_dir, name)
        if os.path.isdir(src_path):
            tf.add(src_path, arcname=dst_path, filter=exclude_pycache)
        elif os.path.isfile(src_path):
            tf.add(src_path, arcname=dst_path)

    tf.add(str(module.path), arcname=pjoin(tf_dir, module.path.name), filter=exclude_pycache)
    tf.add(str(ini_path), arcname=pjoin(tf_dir, 'flit.ini'))
    add_if_exists('docs')
    add_if_exists('tests')
    add_if_exists('LICENSE')
    add_if_exists('README.rst')

    before, extra = [], []
    if module.is_package:
        packages, package_data = auto_packages(str(module.path))
        before.append("packages=\\\n%s\n" % pformat(packages))
        before.append("package_data=\\\n%s\n" % pformat(package_data))
        extra.append("packages=packages,".format([module.name]))
        extra.append("package_data=package_data,".format([module.name]))
    else:
        extra.append("py_modules={!r},".format([module.name]))
    # TODO: Dependencies, scripts

    setup_py = SETUP.format(
        before='\n'.join(before),
        name=metadata.name,
        version=metadata.version,
        description=metadata.summary,
        author=metadata.author,
        author_email=metadata.author_email,
        url=metadata.home_page,
        extra='\n      '.join(extra),
    ).encode('utf-8')
    ti = tarfile.TarInfo(pjoin(tf_dir, 'setup.py'))
    ti.size = len(setup_py)
    tf.addfile(ti, io.BytesIO(setup_py))

    pkg_info = PKG_INFO.format(
        name=metadata.name,
        version=metadata.version,
        summary=metadata.summary,
        home_page=metadata.home_page,
        author=metadata.author,
        author_email=metadata.author_email,
    ).encode('utf-8')
    ti = tarfile.TarInfo(pjoin(tf_dir, 'PKG-INFO'))
    ti.size = len(pkg_info)
    tf.addfile(ti, io.BytesIO(pkg_info))

    tf.close()

    print("Built", target)

if __name__ == '__main__':
    make_sdist()
