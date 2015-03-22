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

class Installer(object):
    def __init__(self, module, user=True, symlink=False):
        self.module = module
        self.user = user
        self.symlink = symlink
        self.installed_files = []

    def install_scripts(self, script_defs, scripts_dir):
        for name, (module, func) in script_defs.items():
            script_file = pathlib.Path(scripts_dir) / name
            log.debug('Writing script to %s', script_file)
            with script_file.open('w') as f:
                f.write(common.script_template.format(
                    interpreter=sys.executable,
                    module=module,
                    func=func
                ))
            script_file.chmod(0o755)

            self.installed_files.append(script_file)

            if sys.platform == 'win32':
                cmd_file = script_file.with_suffix('.cmd')
                cmd = '"{python}" "%~dp0\{script}" %*\r\n'.format(
                            python=sys.executable, script=name)
                log.debug("Writing script wrapper to %s", cmd_file)
                with cmd_file.open('w') as f:
                    f.write(cmd)

                self.installed_files.append(cmd_file)

    def _record_installed_directory(self, path):
        for dirpath, dirnames, files in os.walk(path):
            for f in files:
                self.installed_files.append(os.path.join(dirpath, f))

    def install(self):
        """Install a module/package into site-packages, and create its scripts.
        """
        dirs = get_dirs(user=self.user)
        dst = os.path.join(dirs['purelib'], self.module.path.name)
        if os.path.lexists(dst):
            if os.path.isdir(dst) and not os.path.islink(dst):
                shutil.rmtree(dst)
            else:
                os.unlink(dst)

        src = str(self.module.path)
        if self.symlink:
            log.info("Symlinking %s -> %s", src, dst)
            os.symlink(str(self.module.path.resolve()), dst)
            self.installed_files.append(dst)
        elif self.module.path.is_dir():
            log.info("Copying directory %s -> %s", src, dst)
            shutil.copytree(src, dst)
            self._record_installed_directory(dst)
        else:
            log.info("Copying file %s -> %s", src, dst)
            shutil.copy2(src, dst)
            self.installed_files.append(dst)

        scripts = read_pkg_ini(self.module.ini_file)['scripts']
        self.install_scripts(scripts, dirs['scripts'])

        self.write_dist_info(dirs['purelib'])

    def write_dist_info(self, site_pkgs):
        # Record metadata about installed files to give pip a fighting chance of
        # uninstalling it correctly.
        module_info = common.get_info_from_module(self.module)
        egg_info = pathlib.Path(site_pkgs) / '{}-{}.egg-info'.format(
                                       self.module.name, module_info['version'])
        try:
            egg_info.mkdir()
        except FileExistsError:
            shutil.rmtree(str(egg_info))
            egg_info.mkdir()

        # Not sure what this is for, but it's easy to do, and perhaps it will
        # placate the heathen gods of packaging.
        with (egg_info / 'top_level.txt').open('w') as f:
            f.write(self.module.name)
        self.installed_files.append(egg_info / 'top_level.txt')

        with (egg_info / 'installed-files.txt').open('w') as f:
            for path in self.installed_files:
                rel = os.path.relpath(str(path), str(egg_info))
                f.write(rel + '\n')
