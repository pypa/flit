import configparser
import contextlib
from datetime import datetime
import hashlib
import io
import logging
import os
import re
import zipfile

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
    def __init__(self, ini_path, upload=False, verify_metadata=False, repo='pypi'):
        """Build a wheel from a module/package
        """
        self.ini_path = ini_path
        self.directory = ini_path.parent
        self.dist_dir = self.directory / 'dist'
        try:
            self.dist_dir.mkdir()
        except FileExistsError:
            pass

        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)
        self.metadata = common.make_metadata(self.module, self.ini_info)
        self.upload=upload
        self.verify_metadata=verify_metadata
        self.repo = repo

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
        self.wheel_zip = zipfile.ZipFile(str(self.wheel_path), 'w',
                             compression=zipfile.ZIP_DEFLATED)

    @property
    def wheel_path(self):
        tag = ('py2.' if self.supports_py2 else '') + 'py3-none-any'
        return self.dist_dir / '{}-{}-{}.whl'.format(
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
        hashsum = my_zip_write(self.wheel_zip, full_path, rel_path,
                               date_time=self.source_time_stamp)
        size = os.stat(full_path).st_size
        self.records.append((rel_path, hashsum.hexdigest(), size))

    @contextlib.contextmanager
    def _write_to_zip(self, rel_path):
        sio = io.StringIO()
        yield sio

        log.debug("Writing data to %s in zip file", rel_path)
        date_time = self.source_time_stamp or (2016, 1, 1, 0, 0, 0)
        zi = zipfile.ZipInfo(rel_path, date_time)
        b = sio.getvalue().encode('utf-8')
        hashsum = hashlib.sha256(b)
        self.wheel_zip.writestr(zi, b, compress_type=zipfile.ZIP_DEFLATED)
        self.records.append((rel_path, hashsum.hexdigest(), len(b)))

    def copy_module(self):
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
                                    .startswith(('3', '>3', '>=3'))

    def write_metadata(self):
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
        # Write a record of the files in the wheel
        with self._write_to_zip(self.dist_version + '.dist-info/RECORD') as f:
            for path, hash, size in self.records:
                f.write('{},sha256={},{}\n'.format(path, hash, size))
            # RECORD itself is recorded with no hash or size
            f.write(self.dist_version + '.dist-info/RECORD,,\n')

    def post_build(self):
        if self.verify_metadata:
            from .upload import verify
            verify(self.metadata, self.repo)

        if self.upload:
            from .upload import do_upload
            do_upload(self.wheel_path, self.metadata, self.repo)

    def build(self):
        self.copy_module()
        self.write_metadata()
        self.write_record()

        self.wheel_zip.close()

        self.post_build()


import stat, time
from zipfile import ZipInfo, ZIP_LZMA, _get_compressor, ZIP64_LIMIT, crc32

def my_zip_write(self, filename, arcname=None, compress_type=None,
                 date_time=None):
    """Copy of zipfile.ZipFile.write() with some modifications

    - Allow overriding the timestamp for reproducible builds
    - Calculate a SHA256 hash of the file as we write it and return the hash
      object.
    """
    if not self.fp:
        raise RuntimeError(
            "Attempt to write to ZIP archive that was already closed")

    st = os.stat(filename)
    isdir = stat.S_ISDIR(st.st_mode)
    if date_time is None:
        mtime = time.localtime(st.st_mtime)
        date_time = mtime[0:6]
    # Create ZipInfo instance to store file information
    if arcname is None:
        arcname = filename
    arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
    while arcname[0] in (os.sep, os.altsep):
        arcname = arcname[1:]
    if isdir:
        arcname += '/'
    zinfo = ZipInfo(arcname, date_time)
    zinfo.external_attr = (st[0] & 0xFFFF) << 16      # Unix attributes
    if isdir:
        zinfo.compress_type = zipfile.ZIP_STORED
    elif compress_type is None:
        zinfo.compress_type = self.compression
    else:
        zinfo.compress_type = compress_type

    zinfo.file_size = st.st_size
    zinfo.flag_bits = 0x00
    self.fp.seek(getattr(self, 'start_dir', 0))
    zinfo.header_offset = self.fp.tell()    # Start of header bytes
    if zinfo.compress_type == ZIP_LZMA:
        # Compressed data includes an end-of-stream (EOS) marker
        zinfo.flag_bits |= 0x02

    self._writecheck(zinfo)
    self._didModify = True

    if isdir:
        zinfo.file_size = 0
        zinfo.compress_size = 0
        zinfo.CRC = 0
        zinfo.external_attr |= 0x10  # MS-DOS directory flag
        self.filelist.append(zinfo)
        self.NameToInfo[zinfo.filename] = zinfo
        self.fp.write(zinfo.FileHeader(False))
        self.start_dir = self.fp.tell()
        return

    hashsum = hashlib.sha256()
    cmpr = _get_compressor(zinfo.compress_type)
    with open(filename, "rb") as fp:
        # Must overwrite CRC and sizes with correct data later
        zinfo.CRC = CRC = 0
        zinfo.compress_size = compress_size = 0
        # Compressed size can be larger than uncompressed size
        zip64 = self._allowZip64 and \
            zinfo.file_size * 1.05 > ZIP64_LIMIT
        self.fp.write(zinfo.FileHeader(zip64))
        file_size = 0
        while 1:
            buf = fp.read(1024 * 8)
            if not buf:
                break
            file_size = file_size + len(buf)
            CRC = crc32(buf, CRC) & 0xffffffff
            hashsum.update(buf)
            if cmpr:
                buf = cmpr.compress(buf)
                compress_size = compress_size + len(buf)
            self.fp.write(buf)
    if cmpr:
        buf = cmpr.flush()
        compress_size = compress_size + len(buf)
        self.fp.write(buf)
        zinfo.compress_size = compress_size
    else:
        zinfo.compress_size = file_size
    zinfo.CRC = CRC
    zinfo.file_size = file_size
    if not zip64 and self._allowZip64:
        if file_size > ZIP64_LIMIT:
            raise RuntimeError('File size has increased during compressing')
        if compress_size > ZIP64_LIMIT:
            raise RuntimeError('Compressed size larger than uncompressed size')
    # Seek backwards and write file header (which will now include
    # correct CRC and file sizes)
    self.start_dir = self.fp.tell()       # Preserve current position in file
    self.fp.seek(zinfo.header_offset, 0)
    self.fp.write(zinfo.FileHeader(zip64))
    self.fp.seek(self.start_dir, 0)
    self.filelist.append(zinfo)
    self.NameToInfo[zinfo.filename] = zinfo

    return hashsum
