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
        os.mkdir(scripts_dir)
        purelib_dir = os.path.join(td.name, 'site-packages')
        os.mkdir(purelib_dir)
        self.addCleanup(td.cleanup)
        self.get_dirs_patch = patch('flit.install.get_dirs',
                return_value={'scripts': scripts_dir, 'purelib': purelib_dir})
        self.get_dirs_patch.start()
        self.tmpdir = pathlib.Path(td.name)

    def tearDown(self):
        self.get_dirs_patch.stop()

    def test_install_module(self):
        Installer(samples_dir / 'module1-pkg.ini').install()
        assert_isfile(str(self.tmpdir / 'site-packages' / 'module1.py'))
        assert_isdir(str(self.tmpdir / 'site-packages' / 'module1-0.1.egg-info'))

    def test_install_package(self):
        Installer(samples_dir / 'package1-pkg.ini').install()
        assert_isdir(str(self.tmpdir / 'site-packages' / 'package1'))
        assert_isdir(str(self.tmpdir / 'site-packages' / 'package1-0.1.egg-info'))
        assert_isfile(str(self.tmpdir / 'scripts' / 'pkg_script'))

    def test_symlink_package(self):
        Installer(samples_dir / 'package1-pkg.ini', symlink=True).install()
        assert_islink(str(self.tmpdir / 'site-packages' / 'package1'),
                      to=str(samples_dir / 'package1'))
        assert_isfile(str(self.tmpdir / 'scripts' / 'pkg_script'))
