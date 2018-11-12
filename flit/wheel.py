from base64 import urlsafe_b64encode
import contextlib
from datetime import datetime
import hashlib
import io
import logging
import os
import re
import stat
import sys
import tempfile
from types import SimpleNamespace

if sys.version_info >= (3, 6):
    import zipfile
else:
    import zipfile36 as zipfile

from flit import __version__
from . import common
from . import inifile

log = logging.getLogger(__name__)

wheel_file_template = """\
Wheel-Version: 1.0
Generator: flit {version}
Root-Is-Purelib: true
""".format(version=__version__)

def _write_wheel_file(f, *, supports_py2=False):
    f.write(wheel_file_template)
    if supports_py2:
        f.write("Tag: py2-none-any\n")
    f.write("Tag: py3-none-any\n")


class WheelBuilder:
    def __init__(self, ini_path, target_fp):
        """Build a wheel from a module/package
        """
        self.ini_path = ini_path
        self.directory = ini_path.parent

        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)
        self.metadata = common.make_metadata(self.module, self.ini_info)

        self.records = []
        try:
            # If SOURCE_DATE_EPOCH is set (e.g. by Debian), it's used for
            # timestamps inside the zip file.
            d = datetime.utcfromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']))
            log.info("Zip timestamps will be from SOURCE_DATE_EPOCH: %s", d)
            # zipfile expects a 6-tuple, not a datetime object
            self.source_time_stamp = (d.year, d.month, d.day, d.hour, d.minute, d.second)
        except (KeyError, ValueError):
            # Otherwise, we'll use the mtime of files, and generated files will
            # default to 2016-1-1 00:00:00
            self.source_time_stamp = None

        # Open the zip file ready to write
        self.wheel_zip = zipfile.ZipFile(target_fp, 'w',
                             compression=zipfile.ZIP_DEFLATED)

    @property
    def dist_info(self):
        return common.dist_info_name(self.metadata.name, self.metadata.version)

    @property
    def wheel_filename(self):
        tag = ('py2.' if self.metadata.supports_py2 else '') + 'py3-none-any'
        return '{}-{}-{}.whl'.format(
                re.sub("[^\w\d.]+", "_", self.metadata.name, flags=re.UNICODE),
                re.sub("[^\w\d.]+", "_", self.metadata.version, flags=re.UNICODE),
                tag)

    def _include(self, path):
        name = os.path.basename(path)
        if (name == '__pycache__') or name.endswith('.pyc'):
            return False
        return True

    def _add_file(self, full_path, rel_path):
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
        zinfo.external_attr = (new_mode & 0xFFFF) << 16      # Unix attributes

        if stat.S_ISDIR(st_mode):
            zinfo.external_attr |= 0x10  # MS-DOS directory flag

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

    @contextlib.contextmanager
    def _write_to_zip(self, rel_path):
        sio = io.StringIO()
        yield sio

        log.debug("Writing data to %s in zip file", rel_path)
        # The default is a fixed timestamp rather than the current time, so
        # that building a wheel twice on the same computer can automatically
        # give you the exact same result.
        date_time = self.source_time_stamp or (2016, 1, 1, 0, 0, 0)
        zi = zipfile.ZipInfo(rel_path, date_time)
        b = sio.getvalue().encode('utf-8')
        hashsum = hashlib.sha256(b)
        hash_digest = urlsafe_b64encode(hashsum.digest()).decode('ascii').rstrip('=')
        self.wheel_zip.writestr(zi, b, compress_type=zipfile.ZIP_DEFLATED)
        self.records.append((rel_path, hash_digest, len(b)))

    def copy_module(self):
        log.info('Copying package file(s) from %s', self.module.path)
        if self.module.is_package:
            # Walk the tree and compress it, sorting everything so the order
            # is stable.
            for dirpath, dirs, files in os.walk(str(self.module.path)):
                reldir = os.path.relpath(dirpath, str(self.directory))
                for file in sorted(files):
                    full_path = os.path.join(dirpath, file)
                    if self._include(full_path):
                        self._add_file(full_path, os.path.join(reldir, file))

                dirs[:] = [d for d in sorted(dirs) if self._include(d)]
        else:
            self._add_file(str(self.module.path), self.module.path.name)

    def write_metadata(self):
        log.info('Writing metadata files')

        if self.ini_info['entrypoints']:
            with self._write_to_zip(self.dist_info + '/entry_points.txt') as f:
                common.write_entry_points(self.ini_info['entrypoints'], f)

        for base in ('COPYING', 'LICENSE'):
            for path in sorted(self.directory.glob(base + '*')):
                self._add_file(path, '%s/%s' % (self.dist_info, path.name))

        with self._write_to_zip(self.dist_info + '/WHEEL') as f:
            _write_wheel_file(f, supports_py2=self.metadata.supports_py2)

        with self._write_to_zip(self.dist_info + '/METADATA') as f:
            self.metadata.write_metadata_file(f)

    def write_record(self):
        log.info('Writing the record of files')
        # Write a record of the files in the wheel
        with self._write_to_zip(self.dist_info + '/RECORD') as f:
            for path, hash, size in self.records:
                f.write('{},sha256={},{}\n'.format(path, hash, size))
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
        with open(fd, 'w+b') as fp:
            wb = WheelBuilder(ini_path, fp)
            wb.build()

        wheel_path = wheel_directory / wb.wheel_filename
        os.replace(temp_path, str(wheel_path))
    except:
        os.unlink(temp_path)
        raise

    log.info("Built wheel: %s", wheel_path)
    return SimpleNamespace(builder=wb, file=wheel_path)

def wheel_main(ini_path, upload=False, verify_metadata=False, repo='pypi'):
    """Build a wheel in the dist/ directory, and optionally upload it.
    """
    dist_dir = ini_path.parent / 'dist'
    try:
        dist_dir.mkdir()
    except FileExistsError:
        pass

    wheel_info = make_wheel_in(ini_path, dist_dir)

    if verify_metadata:
        from .upload import verify
        log.warning("'flit wheel --verify-metadata' is deprecated.")
        verify(wheel_info.builder.metadata, repo)

    if upload:
        from .upload import do_upload
        log.warning("'flit wheel --upload' is deprecated; use 'flit publish' instead.")
        do_upload(wheel_info.file, wheel_info.builder.metadata, repo)

    return wheel_info
