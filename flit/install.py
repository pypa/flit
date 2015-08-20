"""Install packages locally for development
"""
import logging
import os
import csv
import pathlib
import shutil
import site
import sys
import tempfile
from subprocess import check_call
import sysconfig

from . import common
from . import inifile

log = logging.getLogger(__name__)

def _requires_dist_to_pip_requirement(requires_dist):
    """Parse "Foo (v); python_version == '2.x'" from Requires-Dist

    Returns pip-style appropriate for requirements.txt.
    """
    env_mark = ''
    if ';' in requires_dist:
        name_version, env_mark = requires_dist.split(';', 1)
    else:
        name_version = requires_dist
    if '(' in name_version:
        # turn 'name (X)' and 'name (<X.Y)'
        # into 'name == X' and 'name < X.Y'
        name, version = name_version.split('(', 1)
        name = name.strip()
        version = version.replace(')', '').strip()
        if not any(c in version for c in '=<>'):
            version = '==' + version
        name_version = name + version
    # re-add environment marker
    return ';'.join([name_version, env_mark])

def get_dirs(user=True):
    """Get the 'scripts' and 'purelib' directories we'll install into.

    This is now a thin wrapper around sysconfig.get_paths(). It's not inlined,
    because some tests mock it out to install to a different location.
    """
    if user:
        if (sys.platform == "darwin") and sysconfig.get_config_var('PYTHONFRAMEWORK'):
            return sysconfig.get_paths('osx_framework_user')
        return sysconfig.get_paths(os.name + '_user')
    else:
        # The default scheme is 'posix_prefix' or 'nt', and should work for e.g.
        # installing into a virtualenv
        return sysconfig.get_paths()


class RootInstallError(Exception):
    def __str__(self):
        return ("Installing packages as root is not recommended. "
            "To allow this, set FLIT_ROOT_INSTALL=1 and try again.")

class Installer(object):
    def __init__(self, ini_path, user=None, symlink=False, deps='all'):
        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)

        log.debug('%s, %s',user, site.ENABLE_USER_SITE)
        if user is None:
            self.user = site.ENABLE_USER_SITE
        else:
            self.user = user
        if (os.getuid() == 0) and (not os.environ.get('FLIT_ROOT_INSTALL')):
            raise RootInstallError

        self.symlink = symlink
        self.deps = deps
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

    def install_requirements(self):
        """Install requirements of a package with pip.

        Creates a temporary requirements.txt from requires_dist metadata.
        """
        # construct the full list of requirements, including dev requirements
        requirements = []

        if self.deps == 'none':
            return
        if self.deps in ('all', 'production'):
            requirements.extend(self.ini_info['metadata'].get('requires_dist', []))
        if self.deps in ('all', 'develop'):
            requirements.extend(self.ini_info['metadata'].get('dev_requires', []))

        # there aren't any requirements, so return
        if len(requirements) == 0:
            return

        requirements = [
            _requires_dist_to_pip_requirement(req_d)
            for req_d in requirements
        ]

        # install the requirements with pip
        cmd = [sys.executable, '-m', 'pip', 'install']
        if self.user:
            cmd.append('--user')
        with tempfile.NamedTemporaryFile(mode='w',
                                         suffix='requirements.txt',
                                         delete=False) as tf:
            tf.file.write('\n'.join(requirements))
        cmd.extend(['-r', tf.name])
        log.info("Installing requirements")
        try:
            check_call(cmd)
        finally:
            os.remove(tf.name)

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

        self.install_requirements()

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
        metadata = common.make_metadata(self.module, self.ini_info)

        dist_info = pathlib.Path(site_pkgs) / '{}-{}.dist-info'.format(
                                            metadata.name, metadata.version)
        try:
            dist_info.mkdir()
        except FileExistsError:
            shutil.rmtree(str(dist_info))
            dist_info.mkdir()

        with (dist_info / 'METADATA').open('w', encoding='utf-8') as f:
            metadata.write_metadata_file(f)
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
