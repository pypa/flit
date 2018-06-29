import os
from pathlib import Path
import pytoml
from shutil import copy
from testpath import assert_isfile
from testpath.tempdir import TemporaryWorkingDirectory

from flit import tomlify

def test_tomlify(samples_dir):
    with TemporaryWorkingDirectory() as td:
        copy(str(samples_dir / 'entrypoints_valid.ini'),
             os.path.join(td, 'flit.ini'))
        copy(str(samples_dir / 'some_entry_points.txt'), td)
        tomlify.main(argv=[])

        pyproject_toml = Path(td, 'pyproject.toml')
        assert_isfile(pyproject_toml)

        with pyproject_toml.open(encoding='utf-8') as f:
            content = pytoml.load(f)

        assert 'build-system' in content
        assert 'tool' in content
        assert 'flit' in content['tool']
        flit_table = content['tool']['flit']
        assert 'metadata' in flit_table
        assert 'scripts' in flit_table
        assert 'entrypoints' in flit_table
