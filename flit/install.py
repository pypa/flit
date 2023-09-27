"""Install packages locally for development
"""
import logging
import os
import os.path as osp
import csv
import json
import pathlib
import random
import shutil
import site
import sys
import tempfile
from subprocess import check_call, check_output
import sysconfig

from flit_core import common
from .config import read_flit_config
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
    return ' ;'.join([name_version, env_mark])

def test_writable_dir(path):
    """Check if a directory is writable.

    Uses os.access() on POSIX, tries creating files on Windows.
    """
    if os.name == 'posix':
        return os.access(path, os.W_OK)

    return _test_writable_dir_win(path)

def _test_writable_dir_win(path):
    # os.access doesn't work on Windows: http://bugs.python.org/issue2528
    # and we can't use tempfile: http://bugs.python.org/issue22107
    basename = 'accesstest_deleteme_fishfingers_custard_'
    alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789'
    for i in range(10):
        name = basename + ''.join(random.choice(alphabet) for _ in range(6))
        file = osp.join(path, name)
        try:
            with open(file, mode='xb'):
                pass
        except FileExistsError:
            continue
        except PermissionError:
            # This could be because there's a directory with the same name.
            # But it's highly unlikely there's a directory called that,
            # so we'll assume it's because the parent directory is not writable.
            return False
        else:
            os.unlink(file)
            return True

    # This should never be reached
    msg = ('Unexpected condition testing for writable directory {!r}. '
           'Please open an issue on flit to debug why this occurred.') # pragma: no cover
    raise EnvironmentError(msg.format(path))  # pragma: no cover

class RootInstallError(Exception):
    def __str__(self):
        return ("Installing packages as root is not recommended. "
            "To allow this, set FLIT_ROOT_INSTALL=1 and try again.")

class DependencyError(Exception):
    def __str__(self):
        return 'To install dependencies for extras, you cannot set deps=none.'

class Installer(object):
    def __init__(self, directory, ini_info, user=None, python=sys.executable,
                 symlink=False, deps='all', extras=(), pth=False):
        self.directory = directory
        self.ini_info = ini_info
        self.python = python
        self.symlink = symlink
        self.pth = pth
        self.deps = deps
        self.extras = extras
        if deps != 'none' and os.environ.get('FLIT_NO_NETWORK', ''):
            self.deps = 'none'
            log.warning('Not installing dependencies, because FLIT_NO_NETWORK is set')
        if deps == 'none' and extras:
            raise DependencyError()

        self.module = common.Module(self.ini_info.module, directory)

        if (hasattr(os, 'getuid') and (os.getuid() == 0) and
                (not os.environ.get('FLIT_ROOT_INSTALL'))):
            raise RootInstallError

        if user is None:
            self.user = self._auto_user(python)
        else:
            self.user = user
        log.debug('User install? %s', self.user)

        self.installed_files = []

    @classmethod
    def from_ini_path(cls, ini_path, user=None, python=sys.executable,
                      symlink=False, deps='all', extras=(), pth=False):
        ini_info = read_flit_config(ini_path)
        return cls(ini_path.parent, ini_info, user=user, python=python,
                   symlink=symlink, deps=deps, extras=extras, pth=pth)

    def _run_python(self, code=None, file=None, extra_args=()):
        if code and file:
            raise ValueError('Specify code or file, not both')
        if not (code or file):
            raise ValueError('Specify code or file')

        if code:
            args = [self.python, '-c', code]
        else:
            args = [self.python, file]
        args.extend(extra_args)
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        # On Windows, shell needs to be True to pick up our local PATH
        # when finding the Python command.
        shell = (os.name == 'nt')
        return check_output(args, shell=shell, env=env).decode('utf-8')

    def _auto_user(self, python):
        """Default guess for whether to do user-level install.

        This should be True for system Python, and False in an env.
        """
        if python == sys.executable:
            user_site = site.ENABLE_USER_SITE
            lib_dir = sysconfig.get_path('purelib')
        else:
            out = self._run_python(code=
                ("import sysconfig, site; "
                 "print(site.ENABLE_USER_SITE); "
                 "print(sysconfig.get_path('purelib'))"))
            user_site, lib_dir = out.split('\n', 1)
            user_site = (user_site.strip() == 'True')
            lib_dir = lib_dir.strip()

        if not user_site:
            # No user site packages - probably a virtualenv
            log.debug('User site packages not available - env install')
            return False

        log.debug('Checking access to %s', lib_dir)
        return not test_writable_dir(lib_dir)

    def install_scripts(self, script_defs, scripts_dir):
        for name, ep in script_defs.items():
            module, func = common.parse_entry_point(ep)
            import_name = func.split('.')[0]
            script_file = pathlib.Path(scripts_dir) / name
            log.info('Writing script to %s', script_file)
            with script_file.open('w', encoding='utf-8') as f:
                f.write(common.script_template.format(
                    interpreter=self.python,
                    module=module,
                    import_name=import_name,
                    func=func
                ))
            script_file.chmod(0o755)

            self.installed_files.append(script_file)

            if sys.platform == 'win32':
                cmd_file = script_file.with_suffix('.cmd')
                cmd = '@echo off\r\n"{python}" "%~dp0\\{script}" %*\r\n'.format(
                            python=self.python, script=name)
                log.debug("Writing script wrapper to %s", cmd_file)
                with cmd_file.open('w') as f:
                    f.write(cmd)

                self.installed_files.append(cmd_file)

    def install_data_dir(self, target_data_dir):
        for src_path in common.walk_data_dir(self.ini_info.data_directory):
            rel_path = os.path.relpath(src_path, self.ini_info.data_directory)
            dst_path = os.path.join(target_data_dir, rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            pathlib.Path(dst_path).unlink(missing_ok=True)
            if self.symlink:
                os.symlink(os.path.realpath(src_path), dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            self.installed_files.append(dst_path)

    def _record_installed_directory(self, path):
        for dirpath, dirnames, files in os.walk(path):
            for f in files:
                self.installed_files.append(osp.join(dirpath, f))

    def _extras_to_install(self):
        extras_to_install = set(self.extras)
        if self.deps == 'all' or 'all' in extras_to_install:
            extras_to_install |= set(self.ini_info.reqs_by_extra.keys())
            # We don’t remove 'all' from the set because there might be an extra called “all”.
        elif self.deps == 'develop':
            extras_to_install |= {'dev', 'doc', 'test'}

        if self.deps != 'none':
            # '.none' is an internal token for normal requirements
            extras_to_install.add('.none')
        log.info("Extras to install for deps %r: %s", self.deps, extras_to_install)
        return extras_to_install

    def install_requirements(self):
        """Install requirements of a package with pip.

        Creates a temporary requirements.txt from requires_dist metadata.
        """
        # construct the full list of requirements, including dev requirements
        requirements = []

        if self.deps == 'none':
            return

        for extra in self._extras_to_install():
            requirements.extend(self.ini_info.reqs_by_extra.get(extra, []))

        # there aren't any requirements, so return
        if len(requirements) == 0:
            return

        requirements = [
            _requires_dist_to_pip_requirement(req_d)
            for req_d in requirements
        ]

        # install the requirements with pip
        cmd = [self.python, '-m', 'pip', 'install']
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

    def install_reqs_my_python_if_needed(self):
        """Install requirements to this environment if needed.

        We can normally get the summary and version number without import the
        module, but if we do need to import it, we may need to install
        its requirements for the Python where flit is running.
        """
        try:
            common.get_info_from_module(self.module, self.ini_info.dynamic_metadata)
        except ImportError:
            if self.deps == 'none':
                raise  # We were asked not to install deps, so bail out.

            log.warning("Installing requirements to Flit's env to import module.")
            user = self.user if (self.python == sys.executable) else None
            i2 = Installer(self.directory, self.ini_info, user=user, deps='production')
            i2.install_requirements()

    def _get_dirs(self, user):
        if self.python == sys.executable:
            return get_dirs(user=user)
        else:
            import json
            path = osp.join(osp.dirname(__file__), '_get_dirs.py')
            args = ['--user'] if user else []
            return json.loads(self._run_python(file=path, extra_args=args))

    def install_directly(self):
        """Install a module/package into site-packages, and create its scripts.
        """
        dirs = self._get_dirs(user=self.user)
        os.makedirs(dirs['purelib'], exist_ok=True)
        os.makedirs(dirs['scripts'], exist_ok=True)

        module_rel_path = self.module.path.relative_to(self.module.source_dir)
        dst = osp.join(dirs['purelib'], module_rel_path)
        if osp.lexists(dst):
            if osp.isdir(dst) and not osp.islink(dst):
                shutil.rmtree(dst)
            else:
                os.unlink(dst)

        # Install requirements to target environment
        self.install_requirements()

        # Install requirements to this environment if we need them to
        # get docstring & version number.
        if self.python != sys.executable:
            self.install_reqs_my_python_if_needed()

        src = self.module.path
        if self.symlink:
            if self.module.in_namespace_package:
                ns_dir = os.path.dirname(dst)
                os.makedirs(ns_dir, exist_ok=True)

            log.info("Symlinking %s -> %s", src, dst)
            os.symlink(src.resolve(), dst)
            self.installed_files.append(dst)
        elif self.pth:
            # .pth points to the the folder containing the module (which is
            # added to sys.path)
            pth_file = pathlib.Path(dirs['purelib'], self.module.name + '.pth')
            log.info("Adding .pth file %s for %s", pth_file, self.module.source_dir)
            pth_file.write_text(str(self.module.source_dir.resolve()), 'utf-8')
            self.installed_files.append(pth_file)
        elif self.module.is_package:
            log.info("Copying directory %s -> %s", src, dst)
            shutil.copytree(src, dst)
            self._record_installed_directory(dst)
        else:
            log.info("Copying file %s -> %s", src, dst)
            os.makedirs(osp.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            self.installed_files.append(dst)

        scripts = self.ini_info.entrypoints.get('console_scripts', {})
        self.install_scripts(scripts, dirs['scripts'])

        self.install_data_dir(dirs['data'])

        self.write_dist_info(dirs['purelib'])

    def install_with_pip(self):
        """Let pip install the project directory

        pip will create an isolated build environment and install build
        dependencies, which means downloading flit_core from PyPI. We ask pip
        to install the project directory (instead of building a temporary wheel
        and asking pip to install it), so pip will record the project directory
        in direct_url.json.
        """
        self.install_reqs_my_python_if_needed()
        extras = self._extras_to_install()
        extras.discard('.none')
        req_with_extras = '{}[{}]'.format(self.directory, ','.join(extras)) \
            if extras else str(self.directory)
        cmd = [self.python, '-m', 'pip', 'install', req_with_extras]
        if self.user:
            cmd.append('--user')
        if self.deps == 'none':
            cmd.append('--no-deps')
        shell = (os.name == 'nt')
        check_call(cmd, shell=shell)

    def write_dist_info(self, site_pkgs):
        """Write dist-info folder, according to PEP 376"""
        metadata = common.make_metadata(self.module, self.ini_info)
        dist_info = pathlib.Path(site_pkgs) / common.dist_info_name(
                                                metadata.name, metadata.version)
        try:
            dist_info.mkdir()
        except FileExistsError:
            shutil.rmtree(str(dist_info))
            dist_info.mkdir()

        with (dist_info / 'METADATA').open('w', encoding='utf-8') as f:
            metadata.write_metadata_file(f)
        self.installed_files.append(dist_info / 'METADATA')

        with (dist_info / 'INSTALLER').open('w', encoding='utf-8') as f:
            f.write('flit')
        self.installed_files.append(dist_info / 'INSTALLER')

        # We only handle explicitly requested installations
        with (dist_info / 'REQUESTED').open('wb'): pass
        self.installed_files.append(dist_info / 'REQUESTED')

        if self.ini_info.entrypoints:
            with (dist_info / 'entry_points.txt').open('w') as f:
                common.write_entry_points(self.ini_info.entrypoints, f)
            self.installed_files.append(dist_info / 'entry_points.txt')

        with (dist_info / 'direct_url.json').open('w', encoding='utf-8') as f:
            json.dump(
                {
                    "url": self.directory.resolve().as_uri(),
                    "dir_info": {"editable": bool(self.symlink or self.pth)}
                },
                f
            )
        self.installed_files.append(dist_info / 'direct_url.json')

        # newline='' because the csv module does its own newline translation
        with (dist_info / 'RECORD').open('w', encoding='utf-8', newline='') as f:
            cf = csv.writer(f)
            for path in sorted(self.installed_files, key=str):
                path = pathlib.Path(path)
                if path.is_symlink() or path.suffix in {'.pyc', '.pyo'}:
                    hash, size = '', ''
                else:
                    hash = 'sha256=' + common.hash_file(str(path))
                    size = path.stat().st_size
                try:
                    path = path.relative_to(site_pkgs)
                except ValueError:
                    pass
                cf.writerow((str(path), hash, size))

            cf.writerow(((dist_info / 'RECORD').relative_to(site_pkgs), '', ''))

    def install(self):
        if self.symlink or self.pth:
            self.install_directly()
        else:
            self.install_with_pip()
