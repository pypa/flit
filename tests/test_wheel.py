import os
from unittest import TestCase

from testpath import assert_isfile

from flit import Importable, wheel

class WheelTests(TestCase):
    def setUp(self):
        self.orig_working_dir = os.getcwd()
        samples_dir = os.path.join(os.path.dirname(__file__), 'samples')
        os.chdir(samples_dir)

    def tearDown(self):
        os.chdir(self.orig_working_dir)

    def test_wheel_module(self):
        i = Importable('module1')
        i.check()
        wheel(i)
        assert_isfile('dist/module1-0.1-py2.py3-none-any.whl')

    def test_wheel_package(self):
        i = Importable('package1')
        i.check()
        wheel(i)
        assert_isfile('dist/package1-0.1-py2.py3-none-any.whl')
