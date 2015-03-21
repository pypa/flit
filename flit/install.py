"""Install packages locally for development
"""
import logging
import os
import pathlib
import shutil
import site
import sys

from . import common
from .inifile import read_pkg_ini

log = logging.getLogger(__name__)

# For the directories where we'll install stuff
_interpolation_vars = {
    'userbase': site.USER_BASE,
    'usersite': site.USER_SITE,
    'py_major': sys.version_info[0],
    'py_minor': sys.version_info[1],
    'prefix'  : sys.prefix,
}

def get_dirs(user=True):
    """Get the 'scripts' and 'purelib' directories we'll install into.

    This is an abbreviated version of distutils.command.install.INSTALL_SCHEMES
    """
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

def record_installed_directory(path, fileslist):
    site_pkgs = os.path.dirname(path)
    for dirpath, dirnames, files in os.walk(path):
        for f in files:
            filepath = os.path.join(dirpath, f)
            from_site_pkgs = os.path.relpath(filepath, site_pkgs)
            # The record is from the .egg-info directory, hence the ../
            fileslist.append(os.path.join('..', from_site_pkgs))

def install(mod, user=True, symlink=False):
    """Install a module/package into site-packages, and create its scripts.
    """
    dirs = get_dirs(user=user)
    dst = os.path.join(dirs['purelib'], mod.path.name)
    if os.path.lexists(dst):
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
        else:
            os.unlink(dst)

    installed_files = []

    src = str(mod.path)
    if symlink:
        log.info("Symlinking %s -> %s", src, dst)
        os.symlink(str(mod.path.resolve()), dst)
        installed_files.append(os.path.join('..', mod.path.name))
    elif mod.path.is_dir():
        log.info("Copying directory %s -> %s", src, dst)
        shutil.copytree(src, dst)
        record_installed_directory()
    else:
        log.info("Copying file %s -> %s", src, dst)
        shutil.copy2(src, dst)
        installed_files.append(os.path.join('..', mod.path.name))

    scripts = read_pkg_ini(mod.ini_file)['scripts']

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

        from_site_pkgs = os.path.relpath(str(script_file), dirs['purelib'])
        installed_files.append(os.path.join('..', from_site_pkgs))

    # Record metadata about installed files to give pip a fighting chance of
    # uninstalling it correctly.
    module_info = common.get_info_from_module(mod)
    egg_info = pathlib.Path(dirs['purelib']) / '{}-{}.egg-info'.format(
                                               mod.name, module_info['version'])
    try:
        egg_info.mkdir()
    except FileExistsError:
        shutil.rmtree(str(egg_info))
        egg_info.mkdir()
    installed_files.append('./')

    # Not sure what this is for, but it's easy to do, and perhaps it will
    # placate the heathen gods of packaging.
    with (egg_info / 'top_level.txt').open('w') as f:
        f.write(mod.name)
    installed_files.append('top_level.txt')

    with (egg_info / 'installed-files.txt').open('w') as f:
        for path in installed_files:
            f.write(path + '\n')
