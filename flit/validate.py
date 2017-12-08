"""Validate various pieces of packaging data"""

import logging
import os
from pathlib import Path
import re
import requests
import sys

log = logging.getLogger(__name__)

def get_cache_dir() -> Path:
    """Locate a platform-appropriate cache directory for flit to use

    Does not ensure that the cache directory exists.
    """
    if os.name == 'posix' and sys.platform != 'darwin':
        # Linux, Unix, AIX, etc.
        # use ~/.cache if empty OR not set
        xdg = os.environ.get("XDG_CACHE_HOME", None) or (
        os.path.expanduser('~/.cache'))
        return Path(xdg, 'flit')

    elif sys.platform == 'darwin':
        return Path(os.path.expanduser('~'), 'Library/Caches/flit')

    else:
        # Windows (hopefully)
        local = os.environ.get('LOCALAPPDATA', None) or (
        os.path.expanduser('~\\AppData\\Local'))
        return Path(local, 'flit')

def _verify_classifiers_cached(classifiers):
    """Check classifiers against the downloaded list of known classifiers"""
    with (get_cache_dir() / 'classifiers.lst').open(encoding='utf-8') as f:
        valid_classifiers = set(l.strip() for l in f)

    invalid = classifiers - valid_classifiers
    return ["Unrecognised classifier: {!r}".format(c)
            for c in sorted(invalid)]


def _download_classifiers():
    """Get the list of valid trove classifiers from PyPI"""
    log.info('Fetching list of valid trove classifiers')
    resp = requests.get(
        'https://pypi.python.org/pypi?%3Aaction=list_classifiers')
    resp.raise_for_status()

    cache_dir = get_cache_dir()
    try:
        cache_dir.mkdir(parents=True)
    except FileExistsError:
        pass
    with (get_cache_dir() / 'classifiers.lst').open('wb') as f:
        f.write(resp.content)


def validate_classifiers(classifiers):
    """Verify trove classifiers from config file.

    Fetches and caches a list of known classifiers from PyPI. Setting the
    environment variable FLIT_NO_NETWORK=1 will skip this if the classifiers
    are not already cached.
    """
    if not classifiers:
        return []

    problems = []
    classifiers = set(classifiers)
    try:
        problems = _verify_classifiers_cached(classifiers)
    except FileNotFoundError as e1:
        # We haven't yet got the classifiers cached
        pass
    else:
        if not problems:
            return []

    # Either we don't have the list, or there were unexpected classifiers
    # which might have been added since we last fetched it. Fetch and cache.

    if os.environ.get('FLIT_NO_NETWORK', ''):
        log.warning(
            "Not checking classifiers, because FLIT_NO_NETWORK is set")
        return []

    # Try to download up-to-date list of classifiers
    try:
        _download_classifiers()
    except requests.ConnectionError:
        # The error you get on a train, going through Oregon, without wifi
        log.warning(
            "Couldn't get list of valid classifiers to check against")
        return problems
    else:
        return _verify_classifiers_cached(classifiers)


def validate_entrypoints(entrypoints):
    """Check that the loaded entrypoints are valid.

    Expects a dict of dicts, e.g.::

        {'console_scripts': {'flit': 'flit:main'}}
    """

    def _is_identifier_attr(s):
        return all(n.isidentifier() for n in s.split('.'))

    problems = []
    for groupname, group in entrypoints.items():
        for k, v in group.items():
            if ':' in v:
                mod, obj = v.split(':', 1)
                valid = _is_identifier_attr(mod) and _is_identifier_attr(obj)
            else:
                valid = _is_identifier_attr(v)

            if not valid:
                problems.append('Invalid entry point in group {}: '
                                '{} = {}'.format(groupname, k, v))
    return problems

def _valid_version_specifier(s):
    for clause in s.split(','):
        if not re.match(r'(~=|===?|!=|<=?|>=?).*$', clause):
            return False
    return True

def validate_requires_python(metadata):
    spec = metadata.get('requires_python', None)
    if spec is None or _valid_version_specifier(spec):
        return []
    return ['Invalid requires-python: {!r}'.format(spec)]

def validate_config(config_info):
    i = config_info
    problems = sum([
        validate_classifiers(i['metadata'].get('classifiers')),
        validate_entrypoints(i['entrypoints']),
        validate_requires_python(i['metadata']),
                   ], [])

    for p in problems:
        log.error(p)
    return problems
