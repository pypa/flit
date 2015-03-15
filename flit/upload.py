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
    d = {
        ":action": action,

        "name": metadata.name,
        "version": metadata.version,

        # additional meta-data
        "metadata_version": '1.2',
        "summary": metadata.summary,
        "home_page": metadata.home_page,
        "author": metadata.author,
        "author_email": metadata.author_email,
        "maintainer": metadata.maintainer,
        "maintainer_email": metadata.maintainer_email,
        "license": metadata.license or 'UNKNOWN',
        "description": metadata.description,
        "keywords": metadata.keywords,
        "platform": metadata.platform or ['UNKNOWN'],
        "classifiers": metadata.classifiers,
        "download_url": metadata.download_url or 'UNKNOWN',
        "supported_platform": metadata.supported_platform,
        # PEP 314
        "provides": metadata.provides,
        "requires": metadata.requires,
        "obsoletes": metadata.obsoletes,
        # Metadata 1.2
        "project_urls": metadata.project_urls,
        "provides_dist": metadata.provides_dist,
        "obsoletes_dist": metadata.obsoletes_dist,
        "requires_dist": metadata.requires_dist,
        "requires_external": metadata.requires_external,
        "requires_python": metadata.requires_python,
      }

    return {k:v for k,v in d.items() if v}

def _attempt_upload(file:Path, metadata:Metadata, repo):
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
    data = build_post_data('submit', metadata)
    import pprint
    pprint.pprint(data)
    resp = requests.post(repo['url'], data=data,
                         auth=(repo['username'], repo['password'])
                        )
    resp.raise_for_status()
    log.info('Registered %s with PyPI', metadata.name)

def do_upload(file:Path, metadata:Metadata, repo_name='pypi'):
    repo = get_repository(repo_name)
    try:
        _attempt_upload(file, metadata, repo)
    except requests.HTTPError as e:
        if e.response.status_code == 403: # forbidden
            # 403 can be because the package doesn't exist, so try registering
            # it and uploading again.
            log.warn('Upload forbidden; attempting to register new package.')
            register(metadata, repo)
            _attempt_upload(file, metadata, repo)
        else:
            raise
