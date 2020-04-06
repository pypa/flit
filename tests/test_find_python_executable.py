import os
import re
import sys

import pytest

from flit import PythonNotFoundError, find_python_executable


def test_default():
    assert find_python_executable(None) == sys.executable


def test_self():
    assert find_python_executable(sys.executable) == sys.executable


def test_abs():
    assert find_python_executable("/usr/bin/python") == "/usr/bin/python"


def test_find_in_path():
    assert os.path.isabs(find_python_executable("python"))


@pytest.mark.parametrize("bad_python_name", ["pyhton", "ls", "."])
def test_exception(bad_python_name: str):
    """Test that an appropriate exception (that contains the error string) is raised."""
    with pytest.raises(PythonNotFoundError, match=re.escape(bad_python_name)):
        find_python_executable(bad_python_name)
