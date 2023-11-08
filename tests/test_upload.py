from contextlib import contextmanager
from tempfile import NamedTemporaryFile
import os
import io
import pathlib
import sys

import pytest
import responses
from testpath import modified_env
from unittest.mock import patch

from flit import upload
from flit.build import ALL_FORMATS
from flit.upload import get_repository, RepoDetails

samples_dir = pathlib.Path(__file__).parent / 'samples'

repo_settings = upload.RepoDetails(
    url=upload.PYPI, username='user', password='pw'
)

pypirc1 = """
[distutils]
index-servers =
    pypi

[pypi]
username: fred
password: s3cret
"""
# That's not a real password. Well, hopefully not.

@contextmanager
def temp_pypirc(content):
    temp_file = NamedTemporaryFile("w+", delete=False)
    try:
        temp_file.write(content)
        temp_file.close()
        yield temp_file.name
    finally:
        os.unlink(temp_file.name)


@responses.activate
def test_upload(copy_sample):
    responses.add(responses.POST, upload.PYPI, status=200)
    td = copy_sample('module1_toml')

    with temp_pypirc(pypirc1) as pypirc, \
        patch('flit.upload.get_repository', return_value=repo_settings):
            upload.main(td / 'pyproject.toml', repo_name='pypi', pypirc_path=pypirc)

    assert len(responses.calls) == 2

def test_get_repository():
    with temp_pypirc(pypirc1) as pypirc:
        repo = upload.get_repository(pypirc_path=pypirc, project_name='foo')
        assert repo.url == upload.PYPI
        assert repo.username == 'fred'
        assert repo.password == 's3cret'

def test_get_repository_env():
    with temp_pypirc(pypirc1) as pypirc, \
        modified_env({
        'FLIT_INDEX_URL': 'https://pypi.example.com',
        'FLIT_USERNAME': 'alice',
        'FLIT_PASSWORD': 'p4ssword',  # Also not a real password
    }):
        repo = upload.get_repository(pypirc_path=pypirc, project_name='foo')
        # Because we haven't specified a repo name, environment variables should
        # have higher priority than the config file.
        assert repo.url == 'https://pypi.example.com'
        assert repo.username == 'alice'
        assert repo.password == 'p4ssword'

@contextmanager
def _fake_keyring(d):
    class FakeKeyring:
        @staticmethod
        def get_password(service_name, username):
            return d.get(service_name, {}).get(username, None)

    class FakeKeyringErrMod:
        class KeyringError(Exception):
            pass

    with patch.dict('sys.modules', {
        'keyring': FakeKeyring(), 'keyring.errors': FakeKeyringErrMod(),
    }):
        yield

pypirc2 = """
[distutils]
index-servers =
    pypi

[pypi]
username: fred
"""

def test_get_repository_keyring(monkeypatch):
    monkeypatch.delenv('FLIT_PASSWORD', raising=False)
    with _fake_keyring({upload.PYPI: {'fred': 'tops3cret'}}):
        repo = get_repository(pypirc_path=io.StringIO(pypirc2), project_name='foo')
    assert repo == RepoDetails(upload.PYPI, username='fred', password='tops3cret')

    for token_key in ['pypi_token:project:foo', 'pypi_token:user:fred']:
        with _fake_keyring({upload.PYPI: {token_key: 'xyz'}}):
            repo = get_repository(pypirc_path=io.StringIO(pypirc2), project_name='foo')
        assert repo == RepoDetails(upload.PYPI, username='__token__', password='xyz')


pypirc3_repo = "https://invalid-repo.inv"
pypirc3_user = "test"
pypirc3_pass = "not_a_real_password"
pypirc3 = f"""
[distutils] =
index-servers =
    test123

[test123]
repository: {pypirc3_repo}
username: {pypirc3_user}
password: {pypirc3_pass}
"""


def test_upload_pypirc_file(copy_sample):
    with temp_pypirc(pypirc3) as pypirc, \
        patch("flit.upload.upload_file") as upload_file:
        td = copy_sample("module1_toml")
        formats = list(ALL_FORMATS)[:1]
        upload.main(
            td / "pyproject.toml",
            formats=set(formats),
            repo_name="test123",
            pypirc_path=pypirc,
        )
        _, _, repo = upload_file.call_args[0]

        assert repo.url == pypirc3_repo
        assert repo.username == pypirc3_user
        assert repo.password == pypirc3_pass


def test_upload_invalid_pypirc_file(copy_sample):
    with patch("flit.upload.upload_file"):
        td = copy_sample("module1_toml")
        formats = list(ALL_FORMATS)[:1]
        with pytest.raises(FileNotFoundError):
            upload.main(
                td / "pyproject.toml",
                formats=set(formats),
                repo_name="test123",
                pypirc_path="./file.invalid",
            )
