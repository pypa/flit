from collections import defaultdict
from copy import copy
from gzip import GzipFile
import io
import logging
import os
from pathlib import Path
from posixpath import join as pjoin
import tarfile

from . import common, inifile

log = logging.getLogger(__name__)


PKG_INFO = """\
Metadata-Version: 1.1
Name: {name}
Version: {version}
Summary: {summary}
Home-page: {home_page}
Author: {author}
Author-email: {author_email}
"""


def clean_tarinfo(ti, mtime=None):
    """Clean metadata from a TarInfo object to make it more reproducible.

    - Set uid & gid to 0
    - Set uname and gname to ""
    - Normalise permissions to 644 or 755
    - Set mtime if not None
    """
    ti = copy(ti)
    ti.uid = 0
    ti.gid = 0
    ti.uname = ''
    ti.gname = ''
    ti.mode = common.normalize_file_permissions(ti.mode)
    if mtime is not None:
        ti.mtime = mtime
    return ti


class SdistBuilder:
    """Builds a minimal sdist

    These minimal sdists should work for PEP 517.
    The class is extended in flit.sdist to make a more 'full fat' sdist,
    which is what should normally be published to PyPI.
    """
    def __init__(self, ini_path=Path('flit.ini')):
        self.ini_path = ini_path
        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)
        self.metadata = common.make_metadata(self.module, self.ini_info)
        self.srcdir = ini_path.parent

    def prep_entry_points(self):
        # Reformat entry points from dict-of-dicts to dict-of-lists
        res = defaultdict(list)
        for groupname, group in self.ini_info['entrypoints'].items():
            for name, ep in sorted(group.items()):
                res[groupname].append('{} = {}'.format(name, ep))

        return dict(res)

    def select_files(self):
        """Pick which files from the source tree will be included in the sdist

        This is overridden in flit itself to use information from a VCS to
        include tests, docs, etc. for a 'gold standard' sdist.
        """
        return list(self.module.iter_files()) + [self.ini_path.name] \
              + self.ini_info['referenced_files']

    def add_setup_py(self, files_to_add, target_tarfile):
        """No-op here; overridden in flit to generate setup.py"""
        pass

    @property
    def dir_name(self):
        return '{}-{}'.format(self.metadata.name, self.metadata.version)

    def build(self, target_dir:Path =None):
        if target_dir is None:
            target_dir = self.ini_path.parent / 'dist'
        if not target_dir.exists():
            target_dir.mkdir(parents=True)
        target = target_dir / '{}-{}.tar.gz'.format(
                        self.metadata.name, self.metadata.version)
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH', '')
        mtime = int(source_date_epoch) if source_date_epoch else None
        gz = GzipFile(str(target), mode='wb', mtime=mtime)
        tf = tarfile.TarFile(str(target), mode='w', fileobj=gz,
                             format=tarfile.PAX_FORMAT)

        try:
            files_to_add = self.select_files()

            for relpath in files_to_add:
                path = self.srcdir / relpath
                ti = tf.gettarinfo(str(path), arcname=pjoin(self.dir_name, relpath))
                ti = clean_tarinfo(ti, mtime)

                if ti.isreg():
                    with path.open('rb') as f:
                        tf.addfile(ti, f)
                else:
                    tf.addfile(ti)  # Symlinks & ?

            self.add_setup_py(files_to_add, tf)

            pkg_info = PKG_INFO.format(
                name=self.metadata.name,
                version=self.metadata.version,
                summary=self.metadata.summary,
                home_page=self.metadata.home_page,
                author=self.metadata.author,
                author_email=self.metadata.author_email,
            ).encode('utf-8')
            ti = tarfile.TarInfo(pjoin(self.dir_name, 'PKG-INFO'))
            ti.size = len(pkg_info)
            tf.addfile(ti, io.BytesIO(pkg_info))

        finally:
            tf.close()
            gz.close()

        log.info("Built sdist: %s", target)
        return target
