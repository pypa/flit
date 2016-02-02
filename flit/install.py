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
from subprocess import check_call, check_output
import sysconfig

from . import common
from . import inifile
from .wheel import WheelBuilder
from ._get_dirs import get_dirs

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


class RootInstallError(Exception):
    def __str__(self):
        return ("Installing packages as root is not recommended. "
            "To allow this, set FLIT_ROOT_INSTALL=1 and try again.")

class Installer(object):
    def __init__(self, ini_path, user=None, python=sys.executable,
                 symlink=False, deps='all'):
        self.ini_path = ini_path
        self.ini_info = inifile.read_pkg_ini(ini_path)
        self.module = common.Module(self.ini_info['module'], ini_path.parent)

        if (hasattr(os, 'getuid') and (os.getuid() == 0) and
                (not os.environ.get('FLIT_ROOT_INSTALL'))):
            raise RootInstallError

        if user is None:
            self.user = self._auto_user(python)
        else:
            self.user = user
        log.debug('User install? %s', self.user)

        self.python = python
        self.symlink = symlink
        self.deps = deps
        self.installed_files = []

    def _auto_user(self, python):
        """Default guess for whether to do user-level install.

        This should be True for system Python, and False in an env.
        """
        if python == sys.executable:
            user_site = site.ENABLE_USER_SITE
            lib_dir = sysconfig.get_path('purelib')
        else:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            out = check_output([python, '-c',
                ("import sysconfig, site; "
                 "print(site.ENABLE_USER_SITE); "
                 "print(sysconfig.get_path('purelib'))")], env=env)
            user_site, lib_dir = out.decode('utf-8').split('\n', 1)
            user_site = (user_site.strip() == 'True')
            lib_dir = lib_dir.strip()

        if not user_site:
            # No user site packages - probably a virtualenv
            log.debug('User site packages not available - env install')
            return False

        log.debug('Checking access to %s', lib_dir)
        if os.name == 'posix':
            return not os.access(lib_dir, os.W_OK)
        else:
            # os.access isn't reliable on Windows, so try creating a file.
            # TODO: What error does Windows raise if this fails?
            try:
                with tempfile.NamedTemporaryFile(dir=lib_dir):
                    pass
                return False
            except OSError:
                return True

    def install_scripts(self, script_defs, scripts_dir):
        for name, (module, func) in script_defs.items():
            script_file = pathlib.Path(scripts_dir) / name
            log.info('Writing script to %s', script_file)
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
        # This *doesn't* use self.python, because we're doing this to make the
        # module importable in our current Python to get docstring & __version__.
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

    def _get_dirs(self, user):
        if self.python == sys.executable:
            return get_dirs()
        else:
            import json
            path = os.path.join(os.path.dirname(__file__), '_get_dirs.py')
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            out = check_output([self.python, path], env=env)
            return json.loads(out.decode('utf-8'))

    def install_directly(self):
        """Install a module/package into site-packages, and create its scripts.
        """
        dirs = self._get_dirs(user=self.user)
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

    def install_with_pip(self):
        self.install_requirements()

        with tempfile.TemporaryDirectory() as td:
            temp_whl = os.path.join(td, 'temp.whl')
            with open(temp_whl, 'w+b') as fp:
                wb = WheelBuilder(self.ini_path, fp)
                wb.build()

            renamed_whl = os.path.join(td, wb.wheel_filename)
            os.rename(temp_whl, renamed_whl)

            cmd = [self.python, '-m', 'pip', 'install', renamed_whl]
            if self.user:
                cmd.append('--user')
            check_call(cmd)

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

    def install(self):
        if self.symlink:
            self.install_directly()
        else:
            self.install_with_pip()
