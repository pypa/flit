import pathlib

import responses
from unittest.mock import patch

from flit import upload, common

samples_dir = pathlib.Path(__file__).parent / 'samples'

repo_settings = {'url': upload.PYPI,
                 'username': 'user',
                 'password': 'pw'
                }

@responses.activate
def test_register():
    responses.add(responses.POST, upload.PYPI, status=200)

    meta, mod = common.metadata_and_module_from_ini_path(samples_dir / 'module1-pkg.ini')
    with patch('flit.upload.get_repository', return_value=repo_settings):
        upload.register(meta, 'pypi')

    assert len(responses.calls) == 1

@responses.activate
def test_verify():
    responses.add(responses.POST, upload.PYPI, status=200)

    meta, mod = common.metadata_and_module_from_ini_path(samples_dir / 'module1-pkg.ini')
    with patch('flit.upload.get_repository', return_value=repo_settings):
        upload.verify(meta, 'pypi')

    assert len(responses.calls) == 1
