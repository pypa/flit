"""Code to communicate with PyPI to register distributions and upload files.

This is cribbed heavily from distutils.command.(upgrade|register), which as part
of Python is under the PSF license.
"""
import configparser
import getpass
import hashlib
import logging
import os
from pathlib import Path
import re
import requests
import sys
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from flit_core.common import make_metadata, Metadata, Module
from .config import read_flit_config

log = logging.getLogger(__name__)

PYPI = "https://upload.pypi.org/legacy/"
PYPIRC_DEFAULT = "~/.pypirc"

SWITCH_TO_HTTPS = (
    "http://pypi.python.org/",
    "http://testpypi.python.org/",
    "http://upload.pypi.org/",
)


@dataclass
class RepoDetails:
    url: str
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def is_pypi(self):
        # Main PyPI (pypi.org) or TestPyPI (test.pypi.org)
        # This is used to guess the URL for the project's HTML page
        return self.url.rstrip('/').endswith('/legacy')


def get_repositories(file="~/.pypirc"):
    """Get the known repositories from a pypirc file.

    This returns a dict keyed by name, of dicts with keys 'url', 'username',
    'password'. Username and password may be None.
    """
    cp = configparser.ConfigParser(interpolation=None)
    if isinstance(file, str):
        file = os.path.expanduser(file)

        if not os.path.isfile(file):
            return {'pypi': RepoDetails(url=PYPI)}

        cp.read(file)
    else:
        cp.read_file(file)

    names = cp.get('distutils', 'index-servers', fallback='pypi').split()

    repos = {}

    for name in names:
        repos[name] = RepoDetails(
            url=cp.get(name, 'repository', fallback=PYPI),
            username=cp.get(name, 'username', fallback=None),
            password=cp.get(name, 'password', fallback=None),
        )

    return repos


def get_repository(pypirc_path="~/.pypirc", name=None, project_name=None):
    """Get the url, username and password for one repository.

    Returns a dict with keys 'url', 'username', 'password'.

    There is a hierarchy of possible sources of information:

    Index URL:
    1. Command line arg --repository (looked up in .pypirc)
    2. $FLIT_INDEX_URL
    3. Repository called 'pypi' from .pypirc
    4. Default PyPI (hardcoded)

    Username:
    1. $FLIT_USERNAME
    2. Repository with specified name (default 'pypi') in .pypirc
    3. Terminal prompt (write to .pypirc if it doesn't exist yet)

    Password:
    1. $FLIT_PASSWORD
    2. Repository with specified name (default 'pypi') in .pypirc
    3. keyring - pypi_token:project:<project_name>
    4. keyring - pypi_token:user:<username>
    5. keyring - username
    6. Terminal prompt (store to keyring if available)
    """
    log.debug("Loading repositories config from %r", pypirc_path)
    repos_cfg = get_repositories(pypirc_path)

    if name is not None:
        repo = repos_cfg[name]
        if 'FLIT_INDEX_URL' in os.environ:
            raise EnvironmentError(
                "Use either FLIT_INDEX_URL or --repository, not both"
            )
    elif 'FLIT_INDEX_URL' in os.environ:
        repo = RepoDetails(url=os.environ['FLIT_INDEX_URL'])
    elif 'pypi' in repos_cfg:
        repo = repos_cfg['pypi']
    else:
        repo = RepoDetails(url=PYPI)

    if repo.url.startswith(SWITCH_TO_HTTPS):
        # Use https for PyPI, even if an http URL was given
        repo.url = 'https' + repo.url[4:]
    elif repo.url.startswith('http://'):
        log.warning("Unencrypted connection - credentials may be visible on "
                    "the network.")

    log.info("Using repository at %s", repo.url)

    if 'FLIT_USERNAME' in os.environ:
        repo.username = os.environ['FLIT_USERNAME']
    if not repo.username and sys.stdin.isatty():
        while not repo.username:
            repo.username = input("Username: ")
        if repo.url == PYPI:
            write_pypirc(repo, pypirc_path)
    elif not repo.username:
        raise Exception("Could not find username for upload.")

    if 'FLIT_PASSWORD' in os.environ:
        repo.password = os.environ['FLIT_PASSWORD']

    if not repo.password:
        token = find_token(repo, project_name)
        if token is not None:
            repo.username = '__token__'
            repo.password = token
        else:
            repo.password = get_password(repo)

    return repo

def write_pypirc(repo, file="~/.pypirc"):
    """Write .pypirc if it doesn't already exist
    """
    file = os.path.expanduser(file)
    if os.path.isfile(file):
        return

    with open(file, 'w', encoding='utf-8') as f:
        f.write("[pypi]\n"
                "username = %s\n" % repo.username)

def get_password(repo: RepoDetails):
    try:
        import keyring, keyring.errors
    except ImportError:  # pragma: no cover
        log.warning("Install keyring to store tokens/passwords securely")
        keyring = None
    else:
        try:
            stored_pw = keyring.get_password(repo.url, repo.username)
            if stored_pw is not None:
                return stored_pw
        except keyring.errors.KeyringError as e:
            log.warning("Could not get password from keyring (%s)", e)

    if sys.stdin.isatty():
        pw = None
        while not pw:
            print('Server  :', repo.url)
            print('Username:', repo.username)
            pw = getpass.getpass('Password: ')
    else:
        raise Exception("Could not find password for upload.")

    if keyring is not None:
        try:
            keyring.set_password(repo.url, repo.username, pw)
            log.info("Stored password with keyring")
        except keyring.errors.KeyringError as e:
            log.warning("Could not store password in keyring (%s)", e)

    return pw


def find_token(repo: RepoDetails, project_name: str):
    # https://packaging.python.org/en/latest/specifications/name-normalization/
    project_name = re.sub(r"[-_.]+", "-", project_name).lower()
    candidate_keys = [f"pypi_token:project:{project_name}"]

    if repo.username is not None:
        candidate_keys.append(f"pypi_token:user:{repo.username}")

    try:
        import keyring, keyring.errors
    except ImportError:  # pragma: no cover
        pass
    else:
        try:
            for key in candidate_keys:
                token = keyring.get_password(repo.url, key)
                if token is not None:
                    return token
        except keyring.errors.KeyringError as e:
            log.warning("Could not get token from keyring (%s)", e)


def build_post_data(action, metadata:Metadata):
    """Prepare the metadata needed for requests to PyPI.
    """
    d = {
        ":action": action,

        "name": metadata.name,
        "version": metadata.version,

        # additional meta-data
        "metadata_version": '2.3',
        "summary": metadata.summary,
        "home_page": metadata.home_page,
        "author": metadata.author,
        "author_email": metadata.author_email,
        "maintainer": metadata.maintainer,
        "maintainer_email": metadata.maintainer_email,
        "license": metadata.license,
        "description": metadata.description,
        "keywords": metadata.keywords,
        "platform": metadata.platform,
        "classifiers": metadata.classifiers,
        "download_url": metadata.download_url,
        "supported_platform": metadata.supported_platform,
        # Metadata 1.1 (PEP 314)
        "provides": metadata.provides,
        "requires": metadata.requires,
        "obsoletes": metadata.obsoletes,
        # Metadata 1.2 (PEP 345)
        "project_urls": metadata.project_urls,
        "provides_dist": metadata.provides_dist,
        "obsoletes_dist": metadata.obsoletes_dist,
        "requires_dist": metadata.requires_dist,
        "requires_external": metadata.requires_external,
        "requires_python": metadata.requires_python,
        # Metadata 2.1 (PEP 566)
        "description_content_type": metadata.description_content_type,
        "provides_extra": metadata.provides_extra,
      }

    return {k:v for k,v in d.items() if v}

def upload_file(file:Path, metadata:Metadata, repo: RepoDetails):
    """Upload a file to an index server, given the index server details.
    """
    data = build_post_data('file_upload', metadata)
    data['protocol_version'] = '1'
    if file.suffix == '.whl':
        data['filetype'] = 'bdist_wheel'
        py2_support = not (metadata.requires_python or '')\
                                    .startswith(('3', '>3', '>=3'))
        data['pyversion'] = ('py2.' if py2_support else '') + 'py3'
    else:
        data['filetype'] = 'sdist'

    with file.open('rb') as f:
        content = f.read()
        files = {'content': (file.name, content)}
        data['md5_digest'] = hashlib.md5(content).hexdigest()
        data['sha256_digest'] = hashlib.sha256(content).hexdigest()

    log.info('Uploading %s...', file)
    resp = requests.post(
        repo.url, data=data, files=files, auth=(repo.username, repo.password),
    )
    resp.raise_for_status()


def do_upload(file:Path, metadata:Metadata, repo: RepoDetails):
    """Upload a file to an index server.
    """
    upload_file(file, metadata, repo)

    if repo.is_pypi:
        domain = urlparse(repo.url).netloc
        if domain.startswith('upload.'):
            domain = domain[7:]
        log.info("Package is at https://%s/project/%s/", domain, metadata.name)
    else:
        log.info("Package is at %s/%s", repo.url, metadata.name)


def main(ini_path, repo_name, pypirc_path=None, formats=None, gen_setup_py=True,
         use_vcs=True):
    """Build and upload wheel and sdist."""
    if pypirc_path is None:
        pypirc_path = PYPIRC_DEFAULT
    elif not os.path.isfile(pypirc_path):
        raise FileNotFoundError("The specified pypirc config file does not exist.")

    ini_info = read_flit_config(ini_path)
    srcdir = ini_path.parent
    module = Module(ini_info.module, srcdir)
    metadata = make_metadata(module, ini_info)
    repo = get_repository(pypirc_path, repo_name, project_name=metadata.name)

    from . import build
    built = build.main(
        ini_path, formats=formats, gen_setup_py=gen_setup_py, use_vcs=use_vcs
    )

    if built.wheel is not None:
        do_upload(built.wheel.file, built.wheel.builder.metadata, repo)
    if built.sdist is not None:
        do_upload(built.sdist.file, built.sdist.builder.metadata, repo)
