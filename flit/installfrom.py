import os.path
import pathlib
import re
import shutil
import site
import subprocess
import sysconfig
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
import zipfile

from requests_download import download
from .install import Installer

address_formats = {
    'github': (r'([\w\d_-]+)/([\w\d_-]+)(/(.+))?$', 'user/project[/commit-tag-or-branch]'),
}

class BadInput(Exception):
    """An error resulting from invalid input"""
    pass

class InvalidAddress(BadInput):
    def __init__(self, address):
        self.address = address

    def __str__(self):
        return "Invalid address: {!r}".format(self.address)

class UnknownAddressType(BadInput):
    def __init__(self, address_type):
        self.address_type = address_type

    def __str__(self):
        return "Unknown address type: {}".format(self.address_type)

class InvalidAddressLocation(BadInput):
    def __init__(self, address_type, location, expected_pattern):
        self.address_type = address_type
        self.location = location
        self.expected_pattern = expected_pattern

    def __str__(self):
        return "Invalid location: {!r}\n{}: addresses should look like {}".format(
            self.location, self.address_type, self.expected_pattern
        )

def parse_address(address):
    if os.path.isfile(address):
        return 'local_file', address
    elif address.startswith(('http://', 'https://')):
        return 'url', address

    if ':' not in address:
        raise InvalidAddress(address)

    address_type, location = address.split(':', 1)

    try:
        location_regex, location_pattern = address_formats[address_type]
    except KeyError:
        raise UnknownAddressType(address_type)

    if not re.match(location_regex, location):
        raise InvalidAddressLocation(address_type, location, location_pattern)

    return address_type, location


def unpack(archive):
    if zipfile.is_zipfile(archive):
        z = zipfile.ZipFile(archive)
        unpacked = tempfile.mkdtemp()
        z.extractall(path=unpacked)
    elif tarfile.is_tarfile(archive):
        t = tarfile.TarFile(archive)
        unpacked = tempfile.mkdtemp()
        t.extractall(path=unpacked)
    else:
        raise RuntimeError('Unknown archive (not zip or tar): %s' % archive)

    files = os.listdir(unpacked)
    if len(files) == 1 and os.path.isdir(os.path.join(unpacked, files[0])):
        return os.path.join(unpacked, files[0])

    return unpacked

def download_unpack(url):
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, urlparse(url).path.split('/')[-1])
        download(url, path)
        unpacked = unpack(path)
    return unpacked

def fetch(address_type, location):
    if address_type == 'local_file':
        return unpack(location)

    if address_type == 'url':
        return download_unpack(location)

    if address_type == 'github':
        m = re.match(address_formats['github'][0], location)
        user, project, committish = m.group(1, 2, 4)
        if committish is None:
            committish = 'master'
        url = 'https://github.com/{}/{}/archive/{}.zip'.format(user, project, committish)
        return download_unpack(url)


def install_local(path, user=False, python=sys.executable):
    p = pathlib.Path(path)
    Installer(p / 'flit.ini', user=user, python=sys.executable,
              deps='production').install()


def installfrom(address, user=None, python=sys.executable):
    if user is None:
        user = site.ENABLE_USER_SITE \
               and not os.access(sysconfig.get_path('purelib'), os.W_OK)

    try:
        return install_local(fetch(*parse_address(address)), user=user, python=python)
    except BadInput as e:
        print(e, file=sys.stderr)
        return 2
