import configparser
import hashlib
import logging
import os
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

def make_wheel(ini_path, upload=None, verify_metadata=None):
    """Build a wheel from a module/package
    """
    directory = ini_path.parent
    ini_info = inifile.read_pkg_ini(ini_path)

    build_dir = directory / 'build' / 'flit'
    try:
        build_dir.mkdir(parents=True)
    except FileExistsError:
        shutil.rmtree(str(build_dir))
        build_dir.mkdir()

    target = common.Module(ini_info['module'], directory)

    # Copy module/package to build directory
    if target.is_package:
        ignore = shutil.ignore_patterns('*.pyc', '__pycache__')
        shutil.copytree(str(target.path), str(build_dir / target.name), ignore=ignore)
    else:
        shutil.copy2(str(target.path), str(build_dir))

    md_dict = {'name': target.name, 'provides': [target.name]}
    md_dict.update(common.get_info_from_module(target))
    md_dict.update(ini_info['metadata'])
    metadata = common.Metadata(md_dict)

    dist_version = metadata.name + '-' + metadata.version
    py2_support = not (metadata.requires_python or '').startswith(('3', '>3', '>=3'))

    dist_info = build_dir / (dist_version + '.dist-info')
    dist_info.mkdir()

    # Write entry points
    if ini_info['scripts']:
        cp = configparser.ConfigParser()
        cp['console_scripts'] = {k: '%s:%s' % v
                                 for (k,v) in ini_info['scripts'].items()}
        log.debug('Writing entry_points.txt in %s', dist_info)
        with (dist_info / 'entry_points.txt').open('w') as f:
            cp.write(f)

    with (dist_info / 'WHEEL').open('w') as f:
        f.write(wheel_file_template)
        if py2_support:
            f.write("Tag: py2-none-any\n")
        f.write("Tag: py3-none-any\n")

    with (dist_info / 'METADATA').open('w') as f:
        metadata.write_metadata_file(f)

    # Generate the record of the files in the wheel
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

    # So far, we've built the wheel file structure in a directory.
    # Now, zip it up into a .whl file.
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

    if verify_metadata is not None:
        from .upload import verify
        verify(metadata, verify_metadata)

    if upload is not None:
        from .upload import do_upload
        do_upload(dist_dir / filename, metadata, upload)
