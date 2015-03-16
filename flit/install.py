import logging
import os
import pathlib
import shutil
import site
import sys

from . import common

log = logging.getLogger(__name__)

_interpolation_vars = {
    'userbase': site.USER_BASE,
    'usersite': site.USER_SITE,
    'py_major': sys.version_info[0],
    'py_minor': sys.version_info[1],
    'prefix'  : sys.prefix,
}

def get_dirs(user=True):
    if user:
        purelib = site.USER_SITE
        if sys.platform == 'win32':
            scripts = "{userbase}/Python{py_major}{py_minor}/Scripts"
        else:
            scripts = "{userbase}/bin"
    elif sys.platform == 'win32':
        scripts = "{prefix}/Scripts",
        purelib = "{prefix}/Lib/site-packages"
    else:
        scripts = "{prefix}/bin"
        purelib = "{prefix}/lib/python{py_major}.{py_minor}/site-packages"

    return {
        'scripts': scripts.format_map(_interpolation_vars),
        'purelib': purelib.format_map(_interpolation_vars),
    }

def install(target, user=True, symlink=False):
    dirs = get_dirs(user=user)
    dst = os.path.join(dirs['purelib'], target.path.name)
    if os.path.lexists(dst):
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
        else:
            os.unlink(dst)

    src = str(target.path)
    if symlink:
        log.info("Symlinking %s -> %s", src, dst)
        os.symlink(str(target.path.resolve()), dst)
    elif target.path.is_dir():
        log.info("Copying directory %s -> %s", src, dst)
        shutil.copytree(src, dst)
    else:
        log.info("Copying file %s -> %s", src, dst)
        shutil.copy2(src, dst)

    scripts = read_pypi_ini(target.ini_file)['scripts']

    for name, (module, func) in scripts.items():
        script_file = pathlib.Path(dirs['scripts']) / name
        log.debug('Writing script to %s', script_file)
        with script_file.open('w') as f:
            f.write(common.script_template.format(
                interpreter=sys.executable,
                module=module,
                func=func
            ))
        script_file.chmod(0o755)
