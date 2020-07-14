from pathlib import Path
import pytest
from unittest import TestCase

from flit_core.common import (
    Module, get_info_from_module, InvalidVersion, NoVersionError, check_version,
    normalize_file_permissions, Metadata
)

samples_dir = Path(__file__).parent / 'samples'

class ModuleTests(TestCase):
    def test_package_importable(self):
        i = Module('package1', samples_dir)
        assert i.path == samples_dir / 'package1'
        assert i.file == samples_dir / 'package1' / '__init__.py'
        assert i.is_package

    def test_module_importable(self):
        i = Module('module1', samples_dir)
        assert i.path == samples_dir / 'module1.py'
        assert not i.is_package

    def test_missing_name(self):
        with self.assertRaises(ValueError):
            i = Module('doesnt_exist', samples_dir)

    def test_conflicting_modules(self):
        with pytest.raises(ValueError, match="Multiple"):
            Module('module1', samples_dir / 'conflicting_modules')

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

        info = get_info_from_module(Module('moduleunimportable', samples_dir))
        self.assertEqual(info, {'summary': 'A sample unimportable module',
                                'version': '0.1'}
                         )

        info = get_info_from_module(Module('module1', samples_dir / 'constructed_version'))
        self.assertEqual(info, {'summary': 'This module has a __version__ that requires runtime interpretation',
                                'version': '1.2.3'}
                         )

        with self.assertRaises(InvalidVersion):
            get_info_from_module(Module('invalid_version1', samples_dir))

    def test_version_raise(self):
        with pytest.raises(InvalidVersion):
            check_version('a.1.0.beta0')

        with pytest.raises(InvalidVersion):
            check_version('3!')

        with pytest.raises(InvalidVersion):
            check_version((1, 2))

        with pytest.raises(NoVersionError):
            check_version(None)

        assert check_version('4.1.0beta1') == '4.1.0b1'
        assert check_version('v1.2') == '1.2'

def test_normalize_file_permissions():
    assert normalize_file_permissions(0o100664) == 0o100644 # regular file
    assert normalize_file_permissions(0o40775) == 0o40755   # directory

@pytest.mark.parametrize(
    ("requires_python", "expected_result"),
    [
        ("", True),
        (">2.7", True),
        ("3", False),
        (">= 3.7", False),
        ("<4, > 3.2", False),
        (">3.4", False),
        (">=2.7, !=3.0.*, !=3.1.*, !=3.2.*", True),
    ],
)
def test_supports_py2(requires_python, expected_result):
    metadata = object.__new__(Metadata)
    metadata.requires_python = requires_python
    result = metadata.supports_py2
    assert result == expected_result
