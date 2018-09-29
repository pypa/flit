"""Validate various pieces of packaging data"""

import logging
import os
from pathlib import Path
import re
import requests
import sys

from .common import InvalidVersion

log = logging.getLogger(__name__)

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
        'https://pypi.org/pypi?%3Aaction=list_classifiers')
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

# Distribution name, not quite the same as a Python identifier
NAME = re.compile(r'^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$', re.IGNORECASE)
r''
VERSION_SPEC = re.compile(r'(~=|===?|!=|<=?|>=?)\s*[A-Z0-9\-_.*+!]+$', re.IGNORECASE)
REQUIREMENT = re.compile(NAME.pattern[:-1] +  # Trim '$'
     r"""\s*(?P<extras>\[.*\])?
         \s*(?P<version>[(=~<>!][^;]*)?
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
            if not _valid_version_specifier(version):
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

def validate_config(config_info):
    i = config_info
    problems = sum([
        validate_classifiers(i['metadata'].get('classifiers')),
        validate_entrypoints(i['entrypoints']),
        validate_name(i['metadata']),
        validate_requires_python(i['metadata']),
        validate_requires_dist(i['metadata']),
        validate_url(i['metadata'].get('home_page', None)),
        validate_project_urls(i['metadata']),
                   ], [])

    for p in problems:
        log.error(p)
    return problems

# Regex below from packaging, via PEP 440. BSD License:
# Copyright (c) Donald Stufft and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
VERSION_PERMISSIVE = re.compile(r"""
    \s*v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
\s*$""", re.VERBOSE)

pre_spellings = {
    'a': 'a', 'alpha': 'a',
    'b': 'b', 'beta': 'b',
    'rc': 'rc', 'c': 'rc', 'pre': 'rc', 'preview': 'rc',
}

def normalise_version(orig_version):
    """Normalise version number according to rules in PEP 440

    Raises InvalidVersion if the version does not match PEP 440. This can be
    overridden with the FLIT_ALLOW_INVALID environment variable.

    https://www.python.org/dev/peps/pep-0440/#normalization
    """
    version = orig_version.lower()
    m = VERSION_PERMISSIVE.match(version)
    if not m:
        if os.environ.get('FLIT_ALLOW_INVALID'):
            log.warning("Invalid version number {!r} allowed by FLIT_ALLOW_INVALID"
                        .format(orig_version))
            return version
        else:
            raise InvalidVersion("Version number {!r} does not match PEP 440 rules"
                                 .format(orig_version))

    components = []
    add = components.append

    epoch, release = m.group('epoch', 'release')
    if epoch is not None:
        add(str(int(epoch)) + '!')
    add('.'.join(str(int(rp)) for rp in release.split('.')))

    pre_l, pre_n = m.group('pre_l', 'pre_n')
    if pre_l is not None:
        pre_l = pre_spellings[pre_l]
        pre_n = '0' if pre_n is None else str(int(pre_n))
        add(pre_l + pre_n)

    post_n1, post_l, post_n2 = m.group('post_n1', 'post_l', 'post_n2')
    if post_n1 is not None:
        add('.post' + str(int(post_n1)))
    elif post_l is not None:
        post_n = '0' if post_n2 is None else str(int(post_n2))
        add('.post' + str(int(post_n)))

    dev_l, dev_n = m.group('dev_l', 'dev_n')
    if dev_l is not None:
        dev_n = '0' if dev_n is None else str(int(dev_n))
        add('.dev' + dev_n)

    local = m.group('local')
    if local is not None:
        local = local.replace('-', '.').replace('_', '.')
        l = [str(int(c)) if c.isdigit() else c
             for c in local.split('.')]
        add('+' + '.'.join(l))

    version = ''.join(components)
    if version != orig_version:
        log.warning("Version number normalised: {!r} -> {!r} (see PEP 440)"
                    .format(orig_version, version))
    return version
