from os.path import isabs, basename, dirname
import os
import re
import sys
import venv

import pytest

from flit import PythonNotFoundError, find_python_executable


def test_default():
    assert find_python_executable(None) == sys.executable


def test_self():
    assert find_python_executable(sys.executable) == sys.executable


def test_abs():
    abs_path = "C:\\PythonXY\\python.exe" if os.name == 'nt' else '/usr/bin/python'
    assert find_python_executable(abs_path) == abs_path


def test_find_in_path():
    assert isabs(find_python_executable("python"))


def test_env(tmp_path):
    path = tmp_path / "venv"
    venv.create(path)

    executable = find_python_executable(path)
    assert basename(dirname(dirname(executable))) == "venv"


def test_env_abs(tmp_path, monkeypatch):
    path = tmp_path / "venv"
    venv.create(path)

    monkeypatch.chdir(tmp_path)
    assert isabs(find_python_executable("venv"))


@pytest.mark.parametrize("bad_python_name", ["pyhton", "ls", "."])
def test_exception(bad_python_name: str):
    """Test that an appropriate exception (that contains the error string) is raised."""
    with pytest.raises(PythonNotFoundError, match=re.escape(bad_python_name)):
        find_python_executable(bad_python_name)
