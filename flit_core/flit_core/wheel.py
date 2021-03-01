from base64 import urlsafe_b64encode
import contextlib
from datetime import datetime
import hashlib
from glob import glob
import io
import logging
import os
import os.path as osp
import stat
import sys
import tempfile
try:
    from types import SimpleNamespace  # Python 3
except ImportError:
    from argparse import Namespace as SimpleNamespace  # Python 2

HAVE_ZIPFILE36 = True
if sys.version_info >= (3, 6):
    import zipfile
else:
    try:
        import zipfile36 as zipfile
    except ImportError:
        import zipfile
        HAVE_ZIPFILE36 = False

from flit_core import __version__
from . import common

log = logging.getLogger(__name__)

wheel_file_template = u"""\
Wheel-Version: 1.0
Generator: flit {version}
Root-Is-Purelib: true
""".format(version=__version__)

def _write_wheel_file(f, supports_py2=False):
    f.write(wheel_file_template)
    if supports_py2:
        f.write(u"Tag: py2-none-any\n")
    f.write(u"Tag: py3-none-any\n")


def _set_zinfo_mode(zinfo, mode):
    # Set the bits for the mode and bit 0xFFFF for “regular file”
    zinfo.external_attr = mode << 16


class WheelBuilder:
    def __init__(self, directory, module, metadata, entrypoints, target_fp):
        """Build a wheel from a module/package
        """
        self.directory = directory
        self.module = module
        self.metadata = metadata
        self.entrypoints = entrypoints

        self.records = []
        try:
            # If SOURCE_DATE_EPOCH is set (e.g. by Debian), it's used for
            # timestamps inside the zip file.
            d = datetime.utcfromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']))
            if HAVE_ZIPFILE36:
                log.info("Zip timestamps will be from SOURCE_DATE_EPOCH: %s", d)
            else:
                log.warning(
                    "Can't use timestamp from SOURCE_DATE_EPOCH: "
                    "Need Python >= 3.6 or the zipfile36 backport for this."
                )
            # zipfile expects a 6-tuple, not a datetime object
            self.source_time_stamp = (d.year, d.month, d.day, d.hour, d.minute, d.second)
        except (KeyError, ValueError):
            # Otherwise, we'll use the mtime of files, and generated files will
            # default to 2016-1-1 00:00:00
            self.source_time_stamp = None

        # Open the zip file ready to write
        self.wheel_zip = zipfile.ZipFile(target_fp, 'w',
                             compression=zipfile.ZIP_DEFLATED)

    @classmethod
    def from_ini_path(cls, ini_path, target_fp):
        # Local import so bootstrapping doesn't try to load toml
        from .config import read_flit_config
        directory = ini_path.parent
        ini_info = read_flit_config(ini_path)
        entrypoints = ini_info.entrypoints
        module = common.Module(ini_info.module, directory)
        metadata = common.make_metadata(module, ini_info)
        return cls(directory, module, metadata, entrypoints, target_fp)

    @property
    def dist_info(self):
        return common.dist_info_name(self.metadata.name, self.metadata.version)

    @property
    def wheel_filename(self):
        dist_name = common.normalize_dist_name(self.metadata.name, self.metadata.version)
        tag = ('py2.' if self.metadata.supports_py2 else '') + 'py3-none-any'
        return '{}-{}.whl'.format(dist_name, tag)

    def _add_file_old(self, full_path, rel_path):
        log.debug("Adding %s to zip file", full_path)
        full_path, rel_path = str(full_path), str(rel_path)
        if os.sep != '/':
            # We always want to have /-separated paths in the zip file and in
            # RECORD
            rel_path = rel_path.replace(os.sep, '/')

        self.wheel_zip.write(full_path, arcname=rel_path)

        hashsum = hashlib.sha256()
        with open(full_path, 'rb') as src:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)

        size = os.stat(full_path).st_size
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode(
            'ascii').rstrip('=')
        self.records.append((rel_path, hash_digest, size))

    def _add_file_zf36(self, full_path, rel_path):
        log.debug("Adding %s to zip file", full_path)
        full_path, rel_path = str(full_path), str(rel_path)
        if os.sep != '/':
            # We always want to have /-separated paths in the zip file and in
            # RECORD
            rel_path = rel_path.replace(os.sep, '/')

        if self.source_time_stamp is None:
            zinfo = zipfile.ZipInfo.from_file(full_path, rel_path)
        else:
            # Set timestamps in zipfile for reproducible build
            zinfo = zipfile.ZipInfo(rel_path, self.source_time_stamp)

        # Normalize permission bits to either 755 (executable) or 644
        st_mode = os.stat(full_path).st_mode
        new_mode = common.normalize_file_permissions(st_mode)
        _set_zinfo_mode(zinfo, new_mode & 0xFFFF)  # Unix attributes

        if stat.S_ISDIR(st_mode):
            zinfo.external_attr |= 0x10  # MS-DOS directory flag

        zinfo.compress_type = zipfile.ZIP_DEFLATED

        hashsum = hashlib.sha256()
        with open(full_path, 'rb') as src, self.wheel_zip.open(zinfo, 'w') as dst:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)
                dst.write(buf)

        size = os.stat(full_path).st_size
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode('ascii').rstrip('=')
        self.records.append((rel_path, hash_digest, size))

    _add_file = _add_file_zf36 if HAVE_ZIPFILE36 else _add_file_old

    @contextlib.contextmanager
    def _write_to_zip(self, rel_path, mode=0o644):
        sio = io.StringIO()
        yield sio

        log.debug("Writing data to %s in zip file", rel_path)
        # The default is a fixed timestamp rather than the current time, so
        # that building a wheel twice on the same computer can automatically
        # give you the exact same result.
        date_time = self.source_time_stamp or (2016, 1, 1, 0, 0, 0)
        zi = zipfile.ZipInfo(rel_path, date_time)
        _set_zinfo_mode(zi, mode)
        b = sio.getvalue().encode('utf-8')
        hashsum = hashlib.sha256(b)
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode('ascii').rstrip('=')
        self.wheel_zip.writestr(zi, b, compress_type=zipfile.ZIP_DEFLATED)
        self.records.append((rel_path, hash_digest, len(b)))

    def copy_module(self):
        log.info('Copying package file(s) from %s', self.module.path)
        source_dir = str(self.module.source_dir)

        for full_path in self.module.iter_files():
            rel_path = osp.relpath(full_path, source_dir)
            self._add_file(full_path, rel_path)

    def write_metadata(self):
        log.info('Writing metadata files')

        if self.entrypoints:
            with self._write_to_zip(self.dist_info + '/entry_points.txt') as f:
                common.write_entry_points(self.entrypoints, f)

        for base in ('COPYING', 'LICENSE'):
            for path in sorted(glob(str(self.directory / (base + '*')))):
                self._add_file(path, '%s/%s' % (self.dist_info, osp.basename(path)))

        with self._write_to_zip(self.dist_info + '/WHEEL') as f:
            _write_wheel_file(f, supports_py2=self.metadata.supports_py2)

        with self._write_to_zip(self.dist_info + '/METADATA') as f:
            self.metadata.write_metadata_file(f)

    def write_record(self):
        log.info('Writing the record of files')
        # Write a record of the files in the wheel
        with self._write_to_zip(self.dist_info + '/RECORD') as f:
            for path, hash, size in self.records:
                f.write(u'{},sha256={},{}\n'.format(path, hash, size))
            # RECORD itself is recorded with no hash or size
            f.write(self.dist_info + '/RECORD,,\n')

    def build(self):
        try:
            self.copy_module()
            self.write_metadata()
            self.write_record()
        finally:
            self.wheel_zip.close()

def make_wheel_in(ini_path, wheel_directory):
    # We don't know the final filename until metadata is loaded, so write to
    # a temporary_file, and rename it afterwards.
    (fd, temp_path) = tempfile.mkstemp(suffix='.whl', dir=str(wheel_directory))
    try:
        with io.open(fd, 'w+b') as fp:
            wb = WheelBuilder.from_ini_path(ini_path, fp)
            wb.build()

        wheel_path = wheel_directory / wb.wheel_filename
        os.replace(temp_path, str(wheel_path))
    except:
        os.unlink(temp_path)
        raise

    log.info("Built wheel: %s", wheel_path)
    return SimpleNamespace(builder=wb, file=wheel_path)
