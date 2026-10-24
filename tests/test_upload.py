from contextlib import contextmanager
from tempfile import NamedTemporaryFile
import os
import io
import pathlib

import pytest
import requests
import responses
from testpath import modified_env
from unittest.mock import patch

import flit
from flit import upload
from flit.build import ALL_FORMATS
from flit.upload import get_repository, RepoDetails
from flit_core.common import Metadata

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


# The reason phrase from the report in issue #558.
INDEX_REJECTION = (
    "Invalid value for requires_dist. Error: Can't have direct dependency: "
    "'somedep @ git+https://github.com/whoever/somedep.git'"
)


def _fake_post(status, reason, body, calls):
    def fake_post(url, data=None, files=None, auth=None):
        calls.append(url)
        resp = requests.Response()
        resp.status_code = status
        resp.reason = reason
        resp.url = url
        resp.encoding = 'utf-8'
        resp._content = body.encode('utf-8')
        return resp
    return fake_post


def _metadata():
    return Metadata({'name': 'module1', 'version': '0.1'})


def _wheel(tmp_path):
    path = tmp_path / 'module1-0.1-py3-none-any.whl'
    path.write_bytes(b'not a real wheel')
    return path


def test_upload_file_http_400_uses_index_message(tmp_path):
    calls = []
    with patch('flit.upload.requests.post',
               _fake_post(400, INDEX_REJECTION, INDEX_REJECTION, calls)):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    message = str(exc.value)
    assert message.count(INDEX_REJECTION) == 1
    assert len(calls) == 1


def test_upload_file_http_400_byte_reason_is_not_duplicated(tmp_path):
    def fake_post(url, data=None, files=None, auth=None):
        resp = requests.Response()
        resp.status_code = 400
        resp.reason = INDEX_REJECTION.encode('utf-8')
        resp.url = url
        resp.encoding = 'utf-8'
        resp._content = INDEX_REJECTION.encode('utf-8')
        return resp

    with patch('flit.upload.requests.post', fake_post):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    assert str(exc.value).count(INDEX_REJECTION) == 1


def test_upload_file_http_400_ignores_blank_body(tmp_path):
    with patch('flit.upload.requests.post',
               _fake_post(400, 'Bad Request', '  \n\t  ', [])):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    assert str(exc.value).endswith(' for url: ' + upload.PYPI)
    assert '\n' not in str(exc.value)


def test_upload_file_http_400_appends_plain_body(tmp_path):
    body = "Invalid value for requires_dist. Error: Can't have direct dependency."
    with patch('flit.upload.requests.post',
               _fake_post(400, 'Bad Request', body, [])):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    head, separator, extra = str(exc.value).partition('\n')
    assert 'Bad Request' in head
    assert extra == body


def test_upload_file_http_400_skips_html_and_nul_bodies(tmp_path):
    html = '<!DOCTYPE html><html><body>secret</body></html>'
    with patch('flit.upload.requests.post',
               _fake_post(400, 'Bad Request', html, [])):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    assert 'secret' not in str(exc.value)
    assert '\n' not in str(exc.value)

    with patch('flit.upload.requests.post',
               _fake_post(400, 'Bad Request', 'bad\x00byte', [])):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    assert 'bad' not in str(exc.value)
    assert '\n' not in str(exc.value)


def test_upload_file_http_400_truncates_long_body(tmp_path):
    body = 'x' * (upload._REJECTION_DETAIL_LIMIT + 50)
    with patch('flit.upload.requests.post',
               _fake_post(400, 'Bad Request', body, [])):
        with pytest.raises(upload.UploadRejectedError) as exc:
            upload.upload_file(_wheel(tmp_path), _metadata(), repo_settings)
    extra = str(exc.value).split('\n', 1)[1]
    assert extra == ('x' * upload._REJECTION_DETAIL_LIMIT) + '...'




def test_publish_http_400_exits_without_traceback(copy_sample):
    calls = []
    td = copy_sample('module1_toml')
    with temp_pypirc(pypirc1) as pypirc, \
            patch('flit.upload.get_repository', return_value=repo_settings), \
            patch('flit.upload.requests.post',
                  _fake_post(400, INDEX_REJECTION, INDEX_REJECTION, calls)):
        with pytest.raises(SystemExit) as exc:
            flit.main([
                '-f', str(td / 'pyproject.toml'),
                'publish', '--format', 'wheel',
                '--repository', 'pypi', '--pypirc', pypirc,
            ])
    assert len(calls) == 1
    assert exc.value.code == (
        '400 Client Error: ' + INDEX_REJECTION + ' for url: ' + upload.PYPI
    )


@responses.activate
def test_upload_legacy_url_without_trailing_slash(copy_sample):
    # Warehouse's /legacy upload API requires a trailing slash. Without it the
    # request hits a different resource (404 historically, 405 today). See #179.
    repo = RepoDetails(
        url="https://test.pypi.org/legacy",
        username="user",
        password="pw",
    )
    responses.add(responses.POST, "https://test.pypi.org/legacy/", status=200)
    td = copy_sample("module1_toml")

    with temp_pypirc(pypirc1) as pypirc, patch(
        "flit.upload.get_repository", return_value=repo
    ):
        upload.main(td / "pyproject.toml", repo_name="pypi", pypirc_path=pypirc)

    assert len(responses.calls) == 2
    for call in responses.calls:
        assert call.request.url == "https://test.pypi.org/legacy/"


def test_normalize_repository_url():
    assert (
        upload.normalize_repository_url("https://test.pypi.org/legacy")
        == "https://test.pypi.org/legacy/"
    )
    assert (
        upload.normalize_repository_url("https://upload.pypi.org/legacy")
        == "https://upload.pypi.org/legacy/"
    )
    already = "https://upload.pypi.org/legacy/"
    assert upload.normalize_repository_url(already) == already
    other = "https://pypi.example.com"
    assert upload.normalize_repository_url(other) == other
    with_query = "https://test.pypi.org/legacy?foo=1"
    assert upload.normalize_repository_url(with_query) == "https://test.pypi.org/legacy/?foo=1"


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
