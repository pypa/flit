import os
from pathlib import Path
from unittest import TestCase
import pytest

from flit.common import Module, get_info_from_module, InvalidVersion, check_version

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
        self.assertEqual(info, {'summary': 'Example module',
                                'version': '0.1'}
                         )

        info = get_info_from_module(Module('module2', samples_dir))
        self.assertEqual(info, {'summary': 'Docstring formatted like this.',
                                'version': '7.0'}
                         )

        info = get_info_from_module(Module('package1', samples_dir))
        self.assertEqual(info, {'summary': 'A sample package',
                                'version': '0.1'}
                         )

        with self.assertRaises(InvalidVersion):
            get_info_from_module(Module('invalid_version1', samples_dir))

    def test_version_raise(self):
        with pytest.raises(InvalidVersion):
            check_version('a.1.0.beta0')

        assert check_version('4.1.0b1') == True
        assert check_version('4.1.0beta1') == False


