import configparser
import getpass
import os

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
    print("Using repository at", repos['url'])

    while not repo['username']:
        repo['username'] = input("Username: ")
    while not repo['password']:
        repo['password'] = getpass.getpass()

    return repo

def build_metadata(target, module_info, ini_info):

    return {
        "name": target.name,
        "version": module_info['version'],

        # file content
        "filetype": "bdist_wheel",
        "pyversion": py_version,
        # additional meta-data
        "metadata_version": '1.2',
        "summary": module_info['description'],
        "home_page": ini_info['package']['url'],
        "author": ini_info.get('package', 'author', fallback='UNKNOWN'),
        "author_email": ini_info.get('package', 'author_email', fallback='UNKNOWN'),
        "maintainer": ini_info.get('package', 'maintainer', fallback='UNKNOWN'),
        "maintainer_email": ini_info.get('package', 'maintainer_email', fallback='UNKNOWN'),
        "license": ini_info.get('package', 'license', fallback='UNKNOWN'),
        "description": module_info['long_description'] or 'UNKNOWN',
        "keywords": ini_info.get('package', 'keywords', fallback='UNKNOWN'),
        "platform": ini_info.get('package', 'platform', fallback='').splitlines(),
        "classifiers": ini_info.get('package', 'classifiers', fallback='').splitlines(),
        "download_url": 'UNKNOWN',
        "supported_platform": [],
        "comment": '',
        # PEP 314
        "provides": [],
        "requires": [],  # TODO
        "obsoletes": [],
        # Metadata 1.2
        "project_urls": [],
        "provides_dist": [],
        "obsoletes_dist": [],
        "requires_dist": [],
        "requires_external": [],
        "requires_python": 'UNKNOWN',
    }
