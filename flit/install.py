"""Install packages locally for development
"""
import logging
import os
import csv
import pathlib
import shutil
import site
import sys

from . import common
from . import inifile

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

class RootInstallError(Exception):
    def __str__(self):
        return ("Installing packages as root is not recommended. "
            "To allow this, set FLIT_ROOT_INSTALL=1 and try again.")

class Installer(object):
    def __init__(self, ini_path, user=None, symlink=False):
        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.metadata, self.module = common.metadata_and_module_from_ini_path(ini_path)
        log.debug('%s, %s',user, site.ENABLE_USER_SITE)
        if user is None:
            self.user = site.ENABLE_USER_SITE
        else:
            self.user = user
        if (os.getuid() == 0) and (not os.environ.get('FLIT_ROOT_INSTALL')):
            raise RootInstallError

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
        os.makedirs(dirs['purelib'], exist_ok=True)
        os.makedirs(dirs['scripts'], exist_ok=True)

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

        scripts = self.ini_info['scripts']
        self.install_scripts(scripts, dirs['scripts'])

        self.write_dist_info(dirs['purelib'])

    def write_dist_info(self, site_pkgs):
        """Write dist-info folder, according to PEP 376"""
        dist_info = pathlib.Path(site_pkgs) / '{}-{}.dist-info'.format(
                                       self.metadata.name, self.metadata.version)
        try:
            dist_info.mkdir()
        except FileExistsError:
            shutil.rmtree(str(dist_info))
            dist_info.mkdir()

        with (dist_info / 'METADATA').open('w', encoding='utf-8') as f:
            self.metadata.write_metadata_file(f)
        self.installed_files.append(dist_info / 'METADATA')

        with (dist_info / 'INSTALLER').open('w') as f:
            f.write('flit')
        self.installed_files.append(dist_info / 'INSTALLER')

        # We only handle explicitly requested installations
        with (dist_info / 'REQUESTED').open('w'): pass
        self.installed_files.append(dist_info / 'REQUESTED')

        if self.ini_info['entry_points_file'] is not None:
            shutil.copy(str(self.ini_info['entry_points_file']),
                            str(dist_info / 'entry_points.txt')
                       )
            self.installed_files.append(dist_info / 'entry_points.txt')

        with (dist_info / 'RECORD').open('w', encoding='utf-8') as f:
            cf = csv.writer(f)
            for path in self.installed_files:
                path = pathlib.Path(path)
                if path.is_symlink() or path.suffix in {'.pyc', '.pyo'}:
                    hash, size = '', ''
                else:
                    hash = 'sha256=' + common.hash_file(path)
                    size = path.stat().st_size
                try:
                    path = path.relative_to(site_pkgs)
                except ValueError:
                    pass
                cf.writerow((path, hash, size))

            cf.writerow(((dist_info / 'RECORD').relative_to(site_pkgs), '', ''))
