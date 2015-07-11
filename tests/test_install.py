import os
import pathlib
import tempfile
from unittest import TestCase
from unittest.mock import patch

from testpath import assert_isfile, assert_isdir, assert_islink

from flit.install import Installer

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

    def test_install_module(self):
        Installer(samples_dir / 'module1').install()

        assert_isfile(self.tmpdir / 'site-packages' / 'module1.py')
        assert_isdir(self.tmpdir / 'site-packages' / 'module1-0.1.dist-info')

    def test_install_package(self):
        Installer(samples_dir / 'package1').install()
        assert_isdir(self.tmpdir / 'site-packages' / 'package1')
        assert_isdir(self.tmpdir / 'site-packages' / 'package1-0.1.dist-info')
        assert_isfile(self.tmpdir / 'scripts' / 'pkg_script')

    def test_symlink_package(self):
        Installer(samples_dir / 'package1', symlink=True).install()
        assert_islink(self.tmpdir / 'site-packages' / 'package1',
                      to=str(samples_dir / 'package1'))
        assert_isfile(self.tmpdir / 'scripts' / 'pkg_script')

    def test_dist_name(self):
        Installer(samples_dir / 'package3').install()
        assert_isdir(self.tmpdir / 'site-packages' / 'package3')
        assert_isdir(self.tmpdir / 'site-packages' / 'packagedist1-0.1.dist-info')

    def test_entry_points(self):
        Installer(samples_dir / 'package4').install()
        assert_isfile(self.tmpdir / 'site-packages' / 'package4-0.1.dist-info' / 'entry_points.txt')
