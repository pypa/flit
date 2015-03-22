import os
from pathlib import Path
from unittest import TestCase

from flit import Importable

class ImportableTests(TestCase):
    def setUp(self):
        self.orig_working_dir = os.getcwd()
        samples_dir = os.path.join(os.path.dirname(__file__), 'samples')
        os.chdir(samples_dir)

    def tearDown(self):
        os.chdir(self.orig_working_dir)

    def test_package_importable(self):
        i = Importable('package1')
        i.check()
        assert i.path == Path('package1')

    def test_module_importable(self):
        i = Importable('module1')
        i.check()
        assert i.path == Path('module1.py')

    def test_missing_name(self):
        with self.assertRaises(ValueError):
            i = Importable('doesnt_exist')
