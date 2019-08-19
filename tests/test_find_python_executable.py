import os
import sys

from flit import find_python_executable


def test_default():
    assert find_python_executable(None) == sys.executable


def test_self():
    assert find_python_executable(sys.executable) == sys.executable


def test_abs():
    assert find_python_executable("/usr/bin/python") == "/usr/bin/python"


def test_find_in_path():
    assert os.path.isabs(find_python_executable("python"))
