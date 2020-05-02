import json
import os
import pathlib
import sys
import tempfile
from unittest import TestCase, SkipTest
from unittest.mock import patch

import pytest
from testpath import assert_isfile, assert_isdir, assert_islink, MockCommand

from flit import install
from flit.install import Installer, _requires_dist_to_pip_requirement, DependencyError

samples_dir = pathlib.Path(__file__).parent / 'samples'

class InstallTests(TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        scripts_dir = os.path.join(td.name, 'scripts')
        purelib_dir = os.path.join(td.name, 'site-packages')
        self.addCleanup(td.cleanup)
        self.get_dirs_patch = patch('flit.install.get_dirs',
                return_value={'scripts': scripts_dir, 'purelib': purelib_dir})
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

    def test_pth_package(self):
        Installer.from_ini_path(samples_dir / 'package1' / 'pyproject.toml', pth=True).install()
        assert_isfile(self.tmpdir / 'site-packages' / 'package1.pth')
        with open(str(self.tmpdir / 'site-packages' / 'package1.pth')) as f:
            assert f.read() == str(samples_dir / 'package1')
        assert_isfile(self.tmpdir / 'scripts' / 'pkg_script')
        self._assert_direct_url(
            samples_dir / 'package1', 'package1', '0.1', expected_editable=True
        )

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
                   "json.dump({{'purelib': {purelib!r}, 'scripts': {scripts!r} }}, "
                   "sys.stdout)"
                  ).format(python=sys.executable,
                           purelib=str(self.tmpdir / 'site-packages2'),
                           scripts=str(self.tmpdir / 'scripts2'))

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

    def test_extras_error(self):
        with pytest.raises(DependencyError):
            Installer.from_ini_path(samples_dir / 'requires-requests.toml',
                            user=False, deps='none', extras='dev')

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
