import os
from pathlib import Path
from unittest import TestCase

from flit.common import Module, get_info_from_module

samples_dir = os.path.join(os.path.dirname(__file__), 'samples')

class ModuleTests(TestCase):
    def test_package_importable(self):
        i = Module('package1', samples_dir)
        assert i.path == Path(samples_dir, 'package1')
        assert i.file == Path(samples_dir, 'package1', '__init__.py')
        assert i.is_package

    def test_module_importable(self):
        i = Module('module1', samples_dir)
        assert i.path == Path(samples_dir, 'module1.py')
        assert not i.is_package

    def test_missing_name(self):
        with self.assertRaises(ValueError):
            i = Module('doesnt_exist', samples_dir)

    def test_get_info_from_module(self):
        info = get_info_from_module(Module('module1', samples_dir))
        self.assertEqual(info['summary'], 'Example module')
        self.assertEqual(info['version'], '0.1')
        # TODO Others, since we get all the metadata from the module.
        # self.assertEqual(info['flit_module'], '...')
        # self.assertEqual(info['author'], '...')
        # self.assertEqual(info['author_email'], '...')
        # self.assertEqual(info['home_page'], '...')
        # self.assertEqual(info['scripts'], '...')

        info = get_info_from_module(Module('module2', samples_dir))
        self.assertEqual(info['summary'], 'Docstring formatted like this.')
        self.assertEqual(info['version'], '7.0')
        # TODO Others, as per above

        info = get_info_from_module(Module('package1', samples_dir))
        self.assertEqual(info['summary'], 'A sample package')
        self.assertEqual(info['version'], '0.1')
        # TODO Others, as per above
