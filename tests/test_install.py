import os
import pathlib
import tempfile
from unittest import TestCase
from unittest.mock import patch

from testpath import assert_isfile, assert_isdir, assert_islink

from flit import Importable
from flit.install import Installer

class InstallTests(TestCase):
    def setUp(self):
        self.orig_working_dir = os.getcwd()
        samples_dir = os.path.join(os.path.dirname(__file__), 'samples')
        os.chdir(samples_dir)

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
        os.chdir(self.orig_working_dir)

    def test_install_module(self):
        i = Importable('module1')
        i.check()
        Installer(i).install()
        assert_isfile(str(self.tmpdir / 'site-packages' / 'module1.py'))
        assert_isdir(str(self.tmpdir / 'site-packages' / 'module1-0.1.egg-info'))

    def test_install_package(self):
        i = Importable('package1')
        i.check()
        Installer(i).install()
        assert_isdir(str(self.tmpdir / 'site-packages' / 'package1'))
        assert_isdir(str(self.tmpdir / 'site-packages' / 'package1-0.1.egg-info'))
        assert_isfile(str(self.tmpdir / 'scripts' / 'pkg_script'))

    def test_symlink_package(self):
        i = Importable('package1')
        i.check()
        Installer(i, symlink=True).install()
        assert_islink(str(self.tmpdir / 'site-packages' / 'package1'),
                      to=str(i.path.resolve()))
        assert_isfile(str(self.tmpdir / 'scripts' / 'pkg_script'))
