from contextlib import contextmanager
import io
import pathlib
import sys

import responses
from testpath import modified_env
from unittest.mock import patch

from flit import upload

samples_dir = pathlib.Path(__file__).parent / 'samples'

repo_settings = {'url': upload.PYPI,
                 'username': 'user',
                 'password': 'pw',
                 'is_warehouse': True,
                }

@responses.activate
def test_upload(copy_sample):
    responses.add(responses.POST, upload.PYPI, status=200)
    td = copy_sample('module1_toml')

    with patch('flit.upload.get_repository', return_value=repo_settings):
        upload.main(td / 'pyproject.toml', repo_name='pypi')

    assert len(responses.calls) == 2

pypirc1 = """
[distutils]
index-servers =
    pypi

[pypi]
username: fred
password: s3cret
"""
# That's not a real password. Well, hopefully not.

def test_get_repository():
    repo = upload.get_repository(cfg_file=io.StringIO(pypirc1))
    assert repo['url'] == upload.PYPI
    assert repo['username'] == 'fred'
    assert repo['password'] == 's3cret'

def test_get_repository_env():
    with modified_env({
        'FLIT_INDEX_URL': 'https://pypi.example.com',
        'FLIT_USERNAME': 'alice',
        'FLIT_PASSWORD': 'p4ssword',  # Also not a real password
    }):
        repo = upload.get_repository(cfg_file=io.StringIO(pypirc1))
        # Because we haven't specified a repo name, environment variables should
        # have higher priority than the config file.
        assert repo['url'] == 'https://pypi.example.com'
        assert repo['username'] == 'alice'
        assert repo['password'] == 'p4ssword'

@contextmanager
def _fake_keyring(pw):
    real_keyring = sys.modules.get('keyring', None)
    class FakeKeyring:
        @staticmethod
        def get_password(service_name, username):
            return pw

    sys.modules['keyring'] = FakeKeyring()

    try:
        yield
    finally:
        if real_keyring is None:
            del sys.modules['keyring']
        else:
            sys.modules['keyring'] = real_keyring

pypirc2 = """
[distutils]
index-servers =
    pypi

[pypi]
username: fred
"""

def test_get_repository_keyring():
    with modified_env({'FLIT_PASSWORD': None}), \
            _fake_keyring('tops3cret'):
        repo = upload.get_repository(cfg_file=io.StringIO(pypirc2))

    assert repo['username'] == 'fred'
    assert repo['password'] == 'tops3cret'
