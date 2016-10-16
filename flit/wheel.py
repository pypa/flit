from base64 import urlsafe_b64encode
import configparser
import contextlib
import tempfile
from datetime import datetime
import hashlib
import io
import logging
import os
import re
import sys

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

class EntryPointsConflict(ValueError):
    def __str__(self):
        return ('Please specify console_scripts entry points or scripts in '
            'flit.ini, not both.')

class WheelBuilder:
    def __init__(self, ini_path, target_fp):
        """Build a wheel from a module/package
        """
        self.ini_path = ini_path
        self.directory = ini_path.parent

        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)
        self.metadata = common.make_metadata(self.module, self.ini_info)

        self.dist_version = self.metadata.name + '-' + self.metadata.version
        self.records = []
        try:
            # If SOURCE_DATE_EPOCH is set (e.g. by Debian), it's used for
            # timestamps inside the zip file.
            d = datetime.utcfromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']))
            log.info("Zip timestamps will be from SOURCE_DATE_EPOCH: %s", d)
            # zipfile expects a 6-tuple, not a datetime object
            self.source_time_stamp = (d.year, d.minute, d.day, d.hour, d.minute, d.second)
        except (KeyError, ValueError):
            # Otherwise, we'll use the mtime of files, and generated files will
            # default to 2016-1-1 00:00:00
            self.source_time_stamp = None

        # Open the zip file ready to write
        self.wheel_zip = zipfile.ZipFile(target_fp, 'w',
                             compression=zipfile.ZIP_DEFLATED)

    @property
    def wheel_filename(self):
        tag = ('py2.' if self.supports_py2 else '') + 'py3-none-any'
        return '{}-{}-{}.whl'.format(
                re.sub("[^\w\d.]+", "_", self.metadata.name, re.UNICODE),
                re.sub("[^\w\d.]+", "_", self.metadata.version, re.UNICODE),
                tag)

    def _include(self, path):
        name = os.path.basename(path)
        if (name == '__pycache__') or name.endswith('.pyc'):
            return False
        return True

    def _add_file(self, full_path, rel_path):
        log.debug("Adding %s to zip file", full_path)
        full_path, rel_path = str(full_path), str(rel_path)

        if self.source_time_stamp is None:
            zinfo = zipfile.ZipInfo.from_file(full_path, rel_path)
        else:
            # Set timestamps in zipfile for reproducible build
            zinfo = zipfile.ZipInfo(full_path, self.source_time_stamp)

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

    @property
    def supports_py2(self):
        return not (self.metadata.requires_python or '')\
                                    .startswith(('3', '>3', '>=3', '~=3'))

    def write_metadata(self):
        log.info('Writing metadata files')
        dist_info = self.dist_version + '.dist-info'

        # Write entry points
        if self.ini_info['scripts']:
            cp = configparser.ConfigParser()

            if self.ini_info['entry_points_file'] is not None:
                cp.read(str(self.ini_info['entry_points_file']))
                if 'console_scripts' in cp:
                    raise EntryPointsConflict

            cp['console_scripts'] = {k: '%s:%s' % v
                                     for (k,v) in self.ini_info['scripts'].items()}
            log.debug('Writing entry_points.txt in %s', dist_info)
            with self._write_to_zip(dist_info + '/entry_points.txt') as f:
                cp.write(f)

        elif self.ini_info['entry_points_file'] is not None:
            self._add_file(self.ini_info['entry_points_file'],
                           dist_info + '/entry_points.txt')

        with self._write_to_zip(dist_info + '/WHEEL') as f:
            f.write(wheel_file_template)
            if self.supports_py2:
                f.write("Tag: py2-none-any\n")
            f.write("Tag: py3-none-any\n")

        with self._write_to_zip(dist_info + '/METADATA') as f:
            self.metadata.write_metadata_file(f)

    def write_record(self):
        log.info('Writing the record of files')
        # Write a record of the files in the wheel
        with self._write_to_zip(self.dist_version + '.dist-info/RECORD') as f:
            for path, hash, size in self.records:
                f.write('{},sha256={},{}\n'.format(path, hash, size))
            # RECORD itself is recorded with no hash or size
            f.write(self.dist_version + '.dist-info/RECORD,,\n')

    def build(self):
        self.copy_module()
        self.write_metadata()
        self.write_record()

        self.wheel_zip.close()

def wheel_main(ini_path, upload=False, verify_metadata=False, repo='pypi'):
    """Build a wheel in the dist/ directory, and optionally upload it.
    """
    dist_dir = ini_path.parent / 'dist'
    try:
        dist_dir.mkdir()
    except FileExistsError:
        pass

    # We don't know the final filename until metadata is loaded, so write to
    # a temporary_file, and rename it afterwards.
    (fd, temp_path) = tempfile.mkstemp(suffix='.whl', dir=str(dist_dir))
    with open(fd, 'w+b') as fp:
        wb = WheelBuilder(ini_path, fp)
        wb.build()

    wheel_path = dist_dir / wb.wheel_filename
    os.replace(temp_path, str(wheel_path))
    log.info("Wheel built: %s", wheel_path)

    if verify_metadata:
        from .upload import verify
        verify(wb.metadata, repo)

    if upload:
        from .upload import do_upload
        do_upload(wheel_path, wb.metadata, repo)
