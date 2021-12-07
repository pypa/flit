import os
from pathlib import Path
from flit_core._vendor import tomli
from shutil import copy
from testpath import assert_isfile

from flit import tomlify

samples_dir = Path(__file__).parent / 'samples'

def test_tomlify(copy_sample, monkeypatch):
    td = copy_sample('with_flit_ini')
    monkeypatch.chdir(td)

    tomlify.main(argv=[])

    pyproject_toml = (td / 'pyproject.toml')
    assert_isfile(pyproject_toml)

    with pyproject_toml.open('rb') as f:
        content = tomli.load(f)

    assert 'build-system' in content
    assert 'tool' in content
    assert 'flit' in content['tool']
    flit_table = content['tool']['flit']
    assert 'metadata' in flit_table
    assert 'scripts' in flit_table
    assert 'entrypoints' in flit_table
