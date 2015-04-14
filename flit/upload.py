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
import requests

from .common import Metadata

log = logging.getLogger(__name__)

PYPI = "https://pypi.python.org/pypi"

def get_repositories(file="~/.pypirc"):
    """Get the known repositories from a pypirc file.

    This returns a dict keyed by name, of dicts with keys 'url', 'username',
    'password'. Username and password may be None.
    """
    file = os.path.expanduser(file)

    if not os.path.isfile(file):
        return {'pypi': {
            'url': PYPI, 'username': None, 'password': None,
        }}

    cp = configparser.ConfigParser()
    cp.read(file)

    names = cp.get('distutils', 'index-servers', fallback='pypi').split()

    repos = {}

    for name in names:
        repos[name] = {
            'url': cp.get(name, 'repository', fallback=PYPI),
            'username': cp.get(name, 'username', fallback=None),
            'password': cp.get(name, 'password', fallback=None),
        }

    return repos

def get_repository(name, cfg_file="~/.pypirc"):
    """Get the url, username and password for one repository.

    If username or password are not specified in the config file, the user
    will be prompted to enter them at the terminal.

    Returns a dict with keys 'url', 'username', 'password'.
    """
    repos = get_repositories(cfg_file)

    repo = repos[name]
    if repo['url'] in {'http://pypi.python.org/pypi',
                       'http://testpypi.python.org/pypi'}:
        # Use https for PyPI, even if an http URL was given
        repo['url'] = 'https' + repo['url'][4:]
    log.info("Using repository at %s", repo['url'])

    while not repo['username']:
        repo['username'] = input("Username: ")
    while not repo['password']:
        repo['password'] = getpass.getpass()

    return repo

def build_post_data(action, metadata:Metadata):
    """Prepare the metadata needed for requests to PyPI.
    """
    d = {
        ":action": action,

        "name": metadata.name,
        "version": metadata.version,

        # additional meta-data
        "metadata_version": '1.1',
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
        # PEP 314
        "provides": metadata.provides,
        "requires": metadata.requires,
        "obsoletes": metadata.obsoletes,
        # Metadata 1.2 - PyPI gives a 500 error when I try to supply any of these
        "project_urls": metadata.project_urls,
        "provides_dist": metadata.provides_dist,
        "obsoletes_dist": metadata.obsoletes_dist,
        "requires_dist": metadata.requires_dist,
        "requires_external": metadata.requires_external,
        "requires_python": metadata.requires_python,
      }

    return {k:v for k,v in d.items() if v}

def upload_wheel(file:Path, metadata:Metadata, repo):
    """Upload a .whl file to the PyPI server.
    """
    data = build_post_data('file_upload', metadata)
    data['protocol_version'] = '1'
    data['filetype'] = 'bdist_wheel'
    py2_support = not (metadata.requires_python or '')\
                                .startswith(('3', '>3', '>=3'))
    data['pyversion'] = ('py2.' if py2_support else '') + 'py3'

    with file.open('rb') as f:
        content = f.read()
        files = {'content': (file.name, content)}
        data['md5_digest'] = hashlib.md5(content).hexdigest()

    log.info('Uploading %s...', file)
    resp = requests.post(repo['url'],
                         data=data,
                         files=files,
                         auth=(repo['username'], repo['password']),
                        )
    resp.raise_for_status()

def register(metadata:Metadata, repo):
    """Register a new release with the PyPI server.
    """

    if(type(repo) == str):
        repo = get_repository(repo)
    data = build_post_data('submit', metadata)
    resp = requests.post(repo['url'], data=data,
                         auth=(repo['username'], repo['password'])
                        )
    resp.raise_for_status()
    log.info('Registered %s with PyPI', metadata.name)

def verify(metadata:Metadata, repo_name):
    """Verify the metadata with the PyPI server.
    """
    repo = get_repository(repo_name)
    data = build_post_data('verify', metadata)
    resp = requests.post(repo['url'], data=data,
                         auth=(repo['username'], repo['password'])
                        )
    resp.raise_for_status()
    log.info('Verification succeeded')

def do_upload(file:Path, metadata:Metadata, repo_name='pypi'):
    """Upload a wheel, registering a new package if necessary.
    """
    repo = get_repository(repo_name)
    try:
        upload_wheel(file, metadata, repo)
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            # 403 can happens if the package is not already on PyPI - try
            # registering it and uploading again.
            log.warning('Uploading forbidden; trying to register and upload again')
            register(metadata, repo)
            upload_wheel(file, metadata, repo)
        else:
            raise

    log.info("Package is at %s/%s", repo['url'], metadata.name)
