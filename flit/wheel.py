import configparser
import logging
import os
import re
import shutil
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
        self.build_dir = self.directory / 'build' / 'flit'
        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)
        self.metadata = common.make_metadata(self.module, self.ini_info)
        self.upload=upload
        self.verify_metadata=verify_metadata
        self.repo = repo

        self.dist_version = self.metadata.name + '-' + self.metadata.version
        self.wheel_file = None

    def clean_build_dir(self):
        try:
            self.build_dir.mkdir(parents=True)
        except FileExistsError:
            shutil.rmtree(str(self.build_dir))
            self.build_dir.mkdir()

    def copy_module(self):

        def verbose_copy2(src, dest, *args, **kwargs):
            log.debug('copying %s', src)
            return shutil.copy2(src, dest, *args, **kwargs)


        mod =  self.module
        # Copy module/package to build directory
        if mod.is_package:
            ignore = shutil.ignore_patterns('*.pyc', '__pycache__')
            shutil.copytree(str(mod.path), str(self.build_dir / mod.name),
                    ignore=ignore,
                    copy_function=verbose_copy2
                    )
        else:
            shutil.copy2(str(mod.path), str(self.build_dir))

    @property
    def supports_py2(self):
        return not (self.metadata.requires_python or '')\
                                    .startswith(('3', '>3', '>=3'))

    @property
    def dist_info(self):
        return self.build_dir / (self.dist_version + '.dist-info')

    def write_metadata(self):
        dist_info = self.dist_info
        dist_info.mkdir()

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
            with (dist_info / 'entry_points.txt').open('w') as f:
                cp.write(f)

        elif self.ini_info['entry_points_file'] is not None:
            log.debug('Copying entry_points.txt into %s', dist_info)
            shutil.copy(str(self.ini_info['entry_points_file']),
                        str(dist_info / 'entry_points.txt')
                       )

        with (dist_info / 'WHEEL').open('w') as f:
            f.write(wheel_file_template)
            if self.supports_py2:
                f.write("Tag: py2-none-any\n")
            f.write("Tag: py3-none-any\n")

        with (dist_info / 'METADATA').open('w') as f:
            self.metadata.write_metadata_file(f)

    def write_record(self):
        # Generate the record of the files in the wheel
        records = []
        for dirpath, dirs, files in os.walk(str(self.build_dir)):
            reldir = os.path.relpath(dirpath, str(self.build_dir))
            for f in files:
                relfile = os.path.join(reldir, f)
                file = os.path.join(dirpath, f)
                hash = common.hash_file(file)
                size = os.stat(file).st_size
                records.append((relfile, hash, size))

        with (self.dist_info / 'RECORD').open('w') as f:
            for path, hash, size in records:
                f.write('{},sha256={},{}\n'.format(path, hash, size))
            # RECORD itself is recorded with no hash or size
            f.write(self.dist_version + '.dist-info/RECORD,,\n')

    def zipup(self):
        # So far, we've built the wheel file structure in a directory.
        # Now, zip it up into a .whl file.
        dist_dir = self.directory / 'dist'
        try:
            dist_dir.mkdir()
        except FileExistsError:
            pass

        tag = ('py2.' if self.supports_py2 else '') + 'py3-none-any'
        self.wheel_file = dist_dir / '{}-{}-{}.whl'.format(
                re.sub("[^\w\d.]+", "_", self.metadata.name, re.UNICODE),
                re.sub("[^\w\d.]+", "_", self.metadata.version, re.UNICODE),
                tag)

        with zipfile.ZipFile(str(self.wheel_file), 'w',
                             compression=zipfile.ZIP_DEFLATED) as z:
            for dirpath, dirs, files in os.walk(str(self.build_dir)):
                reldir = os.path.relpath(dirpath, str(self.build_dir))
                for file in files:
                    z.write(os.path.join(dirpath, file), os.path.join(reldir, file))

        log.info("Created %s", self.wheel_file)

    def post_build(self):
        if self.verify_metadata:
            from .upload import verify
            verify(self.metadata, self.repo)

        if self.upload:
            from .upload import do_upload
            do_upload(self.wheel_file, self.metadata, self.repo)

    def build(self):
        self.clean_build_dir()
        self.copy_module()
        self.write_metadata()
        self.write_record()
        self.zipup()
        self.post_build()
