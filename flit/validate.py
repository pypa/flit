"""Validate various pieces of packaging data"""

import errno
import io
import logging
import os
from pathlib import Path
import re
import requests
import sys

from .vendorized.readme.rst import render

log = logging.getLogger(__name__)

CUSTOM_CLASSIFIERS = frozenset({
    # https://github.com/pypa/warehouse/pull/5440
    'Private :: Do Not Upload',
})


def get_cache_dir() -> Path:
    """Locate a platform-appropriate cache directory for flit to use

    Does not ensure that the cache directory exists.
    """
    # Linux, Unix, AIX, etc.
    if os.name == 'posix' and sys.platform != 'darwin':
        # use ~/.cache if empty OR not set
        xdg = os.environ.get("XDG_CACHE_HOME", None) \
              or os.path.expanduser('~/.cache')
        return Path(xdg, 'flit')

    # Mac OS
    elif sys.platform == 'darwin':
        return Path(os.path.expanduser('~'), 'Library/Caches/flit')

    # Windows (hopefully)
    else:
        local = os.environ.get('LOCALAPPDATA', None) \
                or os.path.expanduser('~\\AppData\\Local')
        return Path(local, 'flit')


def _read_classifiers_cached():
    """Reads classifiers from cached file"""
    with (get_cache_dir() / 'classifiers.lst').open(encoding='utf-8') as f:
        valid_classifiers = set(l.strip() for l in f)
    return valid_classifiers


def _download_and_cache_classifiers():
    """Get the list of valid trove classifiers from PyPI"""
    log.info('Fetching list of valid trove classifiers')
    resp = requests.get(
        'https://pypi.org/pypi?%3Aaction=list_classifiers')
    resp.raise_for_status()

    cache_dir = get_cache_dir()
    try:
        cache_dir.mkdir(parents=True)
    except (FileExistsError, PermissionError):
        pass
    except OSError as e:
        # readonly mounted file raises OSError, only these should be captured
        if e.errno != errno.EROFS:
            raise

    try:
        with (cache_dir / 'classifiers.lst').open('wb') as f:
            f.write(resp.content)
    except (PermissionError, FileNotFoundError):
        # cache file could not be created
        pass
    except OSError as e:
        # readonly mounted file raises OSError, only these should be captured
        if e.errno != errno.EROFS:
            raise

    valid_classifiers = set(l.strip() for l in resp.text.splitlines())
    return valid_classifiers


def _verify_classifiers(classifiers, valid_classifiers):
    """Check classifiers against a set of known classifiers"""
    invalid = classifiers - valid_classifiers
    return ["Unrecognised classifier: {!r}".format(c)
            for c in sorted(invalid)]


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
        valid_classifiers = _read_classifiers_cached()
        valid_classifiers.update(CUSTOM_CLASSIFIERS)
        problems = _verify_classifiers(classifiers, valid_classifiers)
    except (FileNotFoundError, PermissionError) as e1:
        # We haven't yet got the classifiers cached or couldn't read it
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
        valid_classifiers = _download_and_cache_classifiers()
    except requests.ConnectionError:
        # The error you get on a train, going through Oregon, without wifi
        log.warning(
            "Couldn't get list of valid classifiers to check against")
        return problems
    valid_classifiers.update(CUSTOM_CLASSIFIERS)
    return _verify_classifiers(classifiers, valid_classifiers)


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

# Distribution name, not quite the same as a Python identifier
NAME = re.compile(r'^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$', re.IGNORECASE)
r''
VERSION_SPEC = re.compile(r'(~=|===?|!=|<=?|>=?)\s*[A-Z0-9\-_.*+!]+$', re.IGNORECASE)
REQUIREMENT = re.compile(NAME.pattern[:-1] +  # Trim '$'
     r"""\s*(?P<extras>\[.*\])?
         \s*(?P<version>[(=~<>!@][^;]*)?
         \s*(?P<envmark>;.*)?
     $""", re.IGNORECASE | re.VERBOSE)
MARKER_OP = re.compile(r'(~=|===?|!=|<=?|>=?|\s+in\s+|\s+not in\s+)')

def validate_name(metadata):
    name = metadata.get('name', None)
    if name is None or NAME.match(name):
        return []
    return ['Invalid name: {!r}'.format(name)]


def _valid_version_specifier(s):
    for clause in s.split(','):
        if not VERSION_SPEC.match(clause.strip()):
            return False
    return True

def validate_requires_python(metadata):
    spec = metadata.get('requires_python', None)
    if spec is None or _valid_version_specifier(spec):
        return []
    return ['Invalid requires-python: {!r}'.format(spec)]

MARKER_VARS = {
    'python_version', 'python_full_version', 'os_name', 'sys_platform',
    'platform_release', 'platform_system', 'platform_version', 'platform_machine',
    'platform_python_implementation', 'implementation_name',
    'implementation_version', 'extra',
}

def validate_environment_marker(em):
    clauses = re.split(r'\s+(?:and|or)\s+', em)
    problems = []
    for c in clauses:
        # TODO: validate parentheses properly. They're allowed by PEP 508.
        parts = MARKER_OP.split(c.strip('()'))
        if len(parts) != 3:
            problems.append("Invalid expression in environment marker: {!r}".format(c))
            continue
        l, op, r = parts
        for var in (l.strip(), r.strip()):
            if var[:1] in {'"', "'"}:
                if len(var) < 2 or var[-1:] != var[:1]:
                    problems.append("Invalid string in environment marker: {}".format(var))
            elif var not in MARKER_VARS:
                problems.append("Invalid variable name in environment marker: {!r}".format(var))
    return problems

def validate_requires_dist(metadata):
    probs = []
    for req in metadata.get('requires_dist', []):
        m = REQUIREMENT.match(req)
        if not m:
            probs.append("Could not parse requirement: {!r}".format(req))
            continue

        extras, version, envmark = m.group('extras', 'version', 'envmark')
        if not (extras is None or all(NAME.match(e.strip())
                                      for e in extras[1:-1].split(','))):
            probs.append("Invalid extras in requirement: {!r}".format(req))
        if version is not None:
            if version.startswith('(') and version.endswith(')'):
                version = version[1:-1]
            if version.startswith('@'):
                pass  # url specifier  TODO: validate URL
            elif not _valid_version_specifier(version):
                print((extras, version, envmark))
                probs.append("Invalid version specifier {!r} in requirement {!r}"
                             .format(version, req))
        if envmark is not None:
            probs.extend(validate_environment_marker(envmark[1:]))
    return probs

def validate_url(url):
    if url is None:
        return []
    probs = []
    if not url.startswith(('http://', 'https://')):
        probs.append("URL {!r} doesn't start with https:// or http://"
                     .format(url))
    elif not url.split('//', 1)[1]:
        probs.append("URL missing address")
    return probs

def validate_project_urls(metadata):
    probs = []
    for prurl in metadata.get('project_urls', []):
        name, url = prurl.split(',', 1)
        url = url.lstrip()
        if not name:
            probs.append("No name for project URL {!r}".format(url))
        elif len(name) > 32:
            probs.append("Project URL name {!r} longer than 32 characters"
                         .format(name))
        probs.extend(validate_url(url))

    return probs


def validate_readme_rst(metadata):
    mimetype = metadata.get('description_content_type', '')

    if mimetype != 'text/x-rst':
        return []

    # rst check
    raw_desc = metadata.get('description', '')
    stream = io.StringIO()
    res = render(raw_desc, stream)
    if not res:
        return [
            ("The file description seems not to be valid rst for PyPI;"
             " it will be interpreted as plain text"),
            stream.getvalue(),
        ]

    return []  # rst rendered OK


def validate_config(config_info):
    i = config_info
    problems = sum([
        validate_classifiers(i.metadata.get('classifiers')),
        validate_entrypoints(i.entrypoints),
        validate_name(i.metadata),
        validate_requires_python(i.metadata),
        validate_requires_dist(i.metadata),
        validate_url(i.metadata.get('home_page', None)),
        validate_project_urls(i.metadata),
        validate_readme_rst(i.metadata)
                   ], [])

    for p in problems:
        log.error(p)
    return problems

