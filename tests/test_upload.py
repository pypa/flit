import pathlib

import pytest
import requests
import responses
from unittest.mock import patch

from flit import upload, common, wheel

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

@responses.activate
def test_upload():
    responses.add(responses.POST, upload.PYPI, status=200)

    with patch('flit.upload.get_repository', return_value=repo_settings):
        wheel.wheel_main(samples_dir / 'module1-pkg.ini', upload='pypi')

    assert len(responses.calls) == 1

@responses.activate
def test_upload_registers():
    with patch('flit.upload.register') as register_mock:
        def upload_callback(request):
            status = 200 if register_mock.called else 403
            return (status, {}, '')

        responses.add_callback(responses.POST, upload.PYPI,
                               callback=upload_callback)

        with patch('flit.upload.get_repository', return_value=repo_settings):
            wheel.wheel_main(samples_dir / 'module1-pkg.ini', upload='pypi')

    assert len(responses.calls) == 2
    assert register_mock.call_count == 1
