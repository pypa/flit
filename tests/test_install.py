import json
import os
import pathlib
import sys
import tempfile
from unittest import TestCase, SkipTest, skipIf
from unittest.mock import patch

import pytest
from testpath import (
    assert_isfile, assert_isdir, assert_islink, assert_not_path_exists, MockCommand
)

from flit import install
from flit.install import Installer, _requires_dist_to_pip_requirement, DependencyError

tests_dir = pathlib.Path(__file__).parent
samples_dir = tests_dir / 'samples'
core_samples_dir = tests_dir.parent / 'flit_core' / 'tests_core' / 'samples'

class InstallTests(TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.get_dirs_patch = patch('flit.install.get_dirs',
                return_value={
                    'scripts': os.path.join(td.name, 'scripts'),
                    'purelib': os.path.join(td.name, 'site-packages'),
                    'data': os.path.join(td.name, 'data'),
                })
        self.get_dirs_patch.start()
        self.tmpdir = pathlib.Path(td.name)

    def tearDown(self):
        self.get_dirs_patch.stop()

    def _assert_direct_url(self, directory, package, version, expected_editable):
        direct_url_file = (
            self.tmpdir
            / 'site-packages'
            / '{}-{}.dist-info'.format(package, version)
            / 'direct_url.json'
        )
        assert_isfile(direct_url_file)
        with direct_url_file.open() as f:
            direct_url = json.load(f)
            assert direct_url['url'].startswith('file:///')
            assert direct_url['url'] == directory.as_uri()
            assert direct_url['dir_info'].get('editable') is expected_editable

    def test_install_module(self):
        Installer.from_ini_path(samples_dir / 'module1_toml' / 'pyproject.toml').install_directly()
        assert_isfile(self.tmpdir / 'site-packages' / 'module1.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.1.dist-info')
        self._assert_direct_url(
            samples_dir / 'module1_toml', 'module1', '0.1', expected_editable=False
        )

    @skipIf(not core_samples_dir.is_dir(), "Missing flit_core samples")
    def test_install_module_pep621(self):
        Installer.from_ini_path(
            core_samples_dir / 'pep621_nodynamic' / 'pyproject.toml',
        ).install_directly()
        assert_isfile(self.tmpdir / 'site-packages' / 'module1.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.3.dist-info')
        self._assert_direct_url(
            core_samples_dir / 'pep621_nodynamic', 'module1', '0.3',
            expected_editable=False
        )

    def test_install_package(self):
        oldcwd = os.getcwd()
        os.chdir(str(samples_dir / 'package1'))
        try:
            Installer.from_ini_path(pathlib.Path('pyproject.toml')).install_directly()
        finally:
            os.chdir(oldcwd)
        assert_isdir(self.tmpdir / 'site-packages' / 'package1')
        assert_isdir(self.tmpdir / 'site-packages' / 'package1-0.1.dist-info')
        assert_isfile(self.tmpdir / 'scripts' / 'pkg_script')
        with (self.tmpdir / 'scripts' / 'pkg_script').open() as f:
            assert f.readline().strip() == "#!" + sys.executable
        self._assert_direct_url(
            samples_dir / 'package1', 'package1', '0.1', expected_editable=False
        )

    def test_install_module_in_src(self):
        oldcwd = os.getcwd()
        os.chdir(samples_dir / 'packageinsrc')
        try:
            Installer.from_ini_path(pathlib.Path('pyproject.toml')).install_directly()
        finally:
            os.chdir(oldcwd)
        assert_isfile(self.tmpdir / 'site-packages' / 'module1.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.1.dist-info')

    def test_install_ns_package_native(self):
        Installer.from_ini_path(samples_dir / 'ns1-pkg' / 'pyproject.toml').install_directly()
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1')
        assert_isfile(self.tmpdir / 'site-packages' / 'ns1' / 'pkg' / '__init__.py')
        assert_not_path_exists(self.tmpdir / 'site-packages' / 'ns1' / '__init__.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1_pkg-0.1.dist-info')

    def test_install_ns_package_module_native(self):
        Installer.from_ini_path(samples_dir / 'ns1-pkg-mod' / 'pyproject.toml').install_directly()
        assert_isfile(self.tmpdir / 'site-packages' / 'ns1' / 'module.py')
        assert_not_path_exists(self.tmpdir / 'site-packages' / 'ns1' / '__init__.py')

    def test_install_ns_package_native_symlink(self):
        if os.name == 'nt':
            raise SkipTest('symlink')
        Installer.from_ini_path(
            samples_dir / 'ns1-pkg' / 'pyproject.toml', symlink=True
        ).install_directly()
        Installer.from_ini_path(
            samples_dir / 'ns1-pkg2' / 'pyproject.toml', symlink=True
        ).install_directly()
        Installer.from_ini_path(
            samples_dir / 'ns1-pkg-mod' / 'pyproject.toml', symlink=True
        ).install_directly()
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1')
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1' / 'pkg')
        assert_islink(self.tmpdir / 'site-packages' / 'ns1' / 'pkg',
                      to=str(samples_dir / 'ns1-pkg' / 'ns1' / 'pkg'))
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1_pkg-0.1.dist-info')

        assert_isdir(self.tmpdir / 'site-packages' / 'ns1' / 'pkg2')
        assert_islink(self.tmpdir / 'site-packages' / 'ns1' / 'pkg2',
                      to=str(samples_dir / 'ns1-pkg2' / 'ns1' / 'pkg2'))
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1_pkg2-0.1.dist-info')

        assert_islink(self.tmpdir / 'site-packages' / 'ns1' / 'module.py',
                      to=samples_dir / 'ns1-pkg-mod' / 'ns1' / 'module.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'ns1_module-0.1.dist-info')

    def test_install_ns_package_pth_file(self):
        Installer.from_ini_path(
            samples_dir / 'ns1-pkg' / 'pyproject.toml', pth=True
        ).install_directly()

        pth_file = self.tmpdir / 'site-packages' / 'ns1.pkg.pth'
        assert_isfile(pth_file)
        assert pth_file.read_text('utf-8').strip() == str(samples_dir / 'ns1-pkg')

    def test_symlink_package(self):
        if os.name == 'nt':
            raise SkipTest("symlink")
        Installer.from_ini_path(samples_dir / 'package1' / 'pyproject.toml', symlink=True).install()
        assert_islink(self.tmpdir / 'site-packages' / 'package1',
                      to=samples_dir / 'package1' / 'package1')
        assert_isfile(self.tmpdir / 'scripts' / 'pkg_script')
        with (self.tmpdir / 'scripts' / 'pkg_script').open() as f:
            assert f.readline().strip() == "#!" + sys.executable
        self._assert_direct_url(
            samples_dir / 'package1', 'package1', '0.1', expected_editable=True
        )

    @skipIf(not core_samples_dir.is_dir(), "Missing flit_core samples")
    def test_symlink_module_pep621(self):
        if os.name == 'nt':
            raise SkipTest("symlink")
        Installer.from_ini_path(
            core_samples_dir / 'pep621_nodynamic' / 'pyproject.toml', symlink=True
        ).install_directly()
        assert_islink(self.tmpdir / 'site-packages' / 'module1.py',
                      to=core_samples_dir / 'pep621_nodynamic' / 'module1.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.3.dist-info')
        self._assert_direct_url(
            core_samples_dir / 'pep621_nodynamic', 'module1', '0.3',
            expected_editable=True
        )

    def test_symlink_module_in_src(self):
        if os.name == 'nt':
            raise SkipTest("symlink")
        oldcwd = os.getcwd()
        os.chdir(samples_dir / 'packageinsrc')
        try:
            Installer.from_ini_path(
                pathlib.Path('pyproject.toml'), symlink=True
            ).install_directly()
        finally:
            os.chdir(oldcwd)
        assert_islink(self.tmpdir / 'site-packages' / 'module1.py',
                      to=(samples_dir / 'packageinsrc' / 'src' / 'module1.py'))
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.1.dist-info')

    def test_pth_package(self):
        Installer.from_ini_path(samples_dir / 'package1' / 'pyproject.toml', pth=True).install()
        assert_isfile(self.tmpdir / 'site-packages' / 'package1.pth')
        with open(str(self.tmpdir / 'site-packages' / 'package1.pth')) as f:
            assert f.read() == str(samples_dir / 'package1')
        assert_isfile(self.tmpdir / 'scripts' / 'pkg_script')
        self._assert_direct_url(
            samples_dir / 'package1', 'package1', '0.1', expected_editable=True
        )

    def test_pth_module_in_src(self):
        oldcwd = os.getcwd()
        os.chdir(samples_dir / 'packageinsrc')
        try:
            Installer.from_ini_path(
                pathlib.Path('pyproject.toml'), pth=True
            ).install_directly()
        finally:
            os.chdir(oldcwd)
        pth_path = self.tmpdir / 'site-packages' / 'module1.pth'
        assert_isfile(pth_path)
        assert pth_path.read_text('utf-8').strip() == str(
            samples_dir / 'packageinsrc' / 'src'
        )
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.1.dist-info')

    def test_dist_name(self):
        Installer.from_ini_path(samples_dir / 'altdistname' / 'pyproject.toml').install_directly()
        assert_isdir(self.tmpdir / 'site-packages' / 'package1')
        assert_isdir(self.tmpdir / 'site-packages' / 'package_dist1-0.1.dist-info')

    def test_entry_points(self):
        Installer.from_ini_path(samples_dir / 'entrypoints_valid' / 'pyproject.toml').install_directly()
        assert_isfile(self.tmpdir / 'site-packages' / 'package1-0.1.dist-info' / 'entry_points.txt')

    def test_pip_install(self):
        ins = Installer.from_ini_path(samples_dir / 'package1' / 'pyproject.toml', python='mock_python',
                        user=False)

        with MockCommand('mock_python') as mock_py:
            ins.install()

        calls = mock_py.get_calls()
        assert len(calls) == 1
        cmd = calls[0]['argv']
        assert cmd[1:4] == ['-m', 'pip', 'install']
        assert cmd[4].endswith('package1')

    def test_symlink_other_python(self):
        if os.name == 'nt':
            raise SkipTest('symlink')
        (self.tmpdir / 'site-packages2').mkdir()
        (self.tmpdir / 'scripts2').mkdir()

        # Called by Installer._auto_user() :
        script1 = ("#!{python}\n"
                   "import sysconfig\n"
                   "print(True)\n"   # site.ENABLE_USER_SITE
                   "print({purelib!r})"  # sysconfig.get_path('purelib')
                  ).format(python=sys.executable,
                           purelib=str(self.tmpdir / 'site-packages2'))

        # Called by Installer._get_dirs() :
        script2 = ("#!{python}\n"
                   "import json, sys\n"
                   "json.dump({{'purelib': {purelib!r}, 'scripts': {scripts!r}, 'data': {data!r} }}, "
                   "sys.stdout)"
                  ).format(python=sys.executable,
                           purelib=str(self.tmpdir / 'site-packages2'),
                           scripts=str(self.tmpdir / 'scripts2'),
                           data=str(self.tmpdir / 'data'),
                  )

        with MockCommand('mock_python', content=script1):
            ins = Installer.from_ini_path(samples_dir / 'package1' / 'pyproject.toml', python='mock_python',
                      symlink=True)
        with MockCommand('mock_python', content=script2):
            ins.install()

        assert_islink(self.tmpdir / 'site-packages2' / 'package1',
                      to=samples_dir / 'package1' / 'package1')
        assert_isfile(self.tmpdir / 'scripts2' / 'pkg_script')
        with (self.tmpdir / 'scripts2' / 'pkg_script').open() as f:
            assert f.readline().strip() == "#!mock_python"

    def test_install_requires(self):
        ins = Installer.from_ini_path(samples_dir / 'requires-requests.toml',
                        user=False, python='mock_python')

        with MockCommand('mock_python') as mockpy:
            ins.install_requirements()
        calls = mockpy.get_calls()
        assert len(calls) == 1
        assert calls[0]['argv'][1:5] == ['-m', 'pip', 'install', '-r']

    @skipIf(not core_samples_dir.is_dir(), "Missing flit_core samples")
    def test_install_reqs_my_python_if_needed_pep621(self):
        ins = Installer.from_ini_path(
            core_samples_dir / 'pep621_nodynamic' / 'pyproject.toml',
            deps='none',
        )

        # This shouldn't try to get version & docstring from the module
        ins.install_reqs_my_python_if_needed()

    def test_extras_error(self):
        with pytest.raises(DependencyError):
            Installer.from_ini_path(samples_dir / 'requires-requests.toml',
                            user=False, deps='none', extras='dev')

    @skipIf(not core_samples_dir.is_dir(), "Missing flit_core samples")
    def test_install_data_dir(self):
        Installer.from_ini_path(
            core_samples_dir / 'with_data_dir' / 'pyproject.toml',
        ).install_directly()
        assert_isfile(self.tmpdir / 'site-packages' / 'module1.py')
        assert_isfile(self.tmpdir / 'data' / 'share' / 'man' / 'man1' / 'foo.1')

    @skipIf(not core_samples_dir.is_dir(), "Missing flit_core samples")
    def test_symlink_data_dir(self):
        if os.name == 'nt':
            raise SkipTest("symlink")
        Installer.from_ini_path(
            core_samples_dir / 'with_data_dir' / 'pyproject.toml', symlink=True
        ).install_directly()
        assert_isfile(self.tmpdir / 'site-packages' / 'module1.py')
        assert_islink(
            self.tmpdir / 'data' / 'share' / 'man' / 'man1' / 'foo.1',
            to=core_samples_dir / 'with_data_dir' / 'data' / 'share' / 'man' / 'man1' / 'foo.1'
        )

@pytest.mark.parametrize(('deps', 'extras', 'installed'), [
    ('none', [], set()),
    ('develop', [], {'pytest ;', 'toml ;'}),
    ('production', [], {'toml ;'}),
    ('all', [], {'toml ;', 'pytest ;', 'requests ;'}),
])
def test_install_requires_extra(deps, extras, installed):
    it = InstallTests()
    try:
        it.setUp()
        ins = Installer.from_ini_path(samples_dir / 'extras' / 'pyproject.toml', python='mock_python',
                        user=False, deps=deps, extras=extras)

        cmd = MockCommand('mock_python')
        get_reqs = (
            "#!{python}\n"
            "import sys\n"
            "with open({recording_file!r}, 'wb') as w, open(sys.argv[-1], 'rb') as r:\n"
            "    w.write(r.read())"
        ).format(python=sys.executable, recording_file=cmd.recording_file)
        cmd.content = get_reqs

        with cmd as mock_py:
            ins.install_requirements()
        with open(mock_py.recording_file) as f:
            str_deps = f.read()
        deps = str_deps.split('\n') if str_deps else []

        assert set(deps) == installed
    finally:
        it.tearDown()

def test_requires_dist_to_pip_requirement():
    rd = 'pathlib2 (>=2.3); python_version == "2.7"'
    assert _requires_dist_to_pip_requirement(rd) == \
        'pathlib2>=2.3 ; python_version == "2.7"'

def test_test_writable_dir_win():
    with tempfile.TemporaryDirectory() as td:
        assert install._test_writable_dir_win(td) is True

        # Ironically, I don't know how to make a non-writable dir on Windows,
        # so although the functionality is for Windows, the test is for Posix
        if os.name != 'posix':
            return

        # Remove write permissions from the directory
        os.chmod(td, 0o444)
        try:
            assert install._test_writable_dir_win(td) is False
        finally:
            os.chmod(td, 0o644)
