import configparser
import logging
import os
from pathlib import Path
import sys

import requests

from . import common

log = logging.getLogger(__name__)

class ConfigError(ValueError):
    pass

metadata_list_fields = {
    'classifiers',
    'requires',
}

metadata_allowed_fields = {
    'module',
    'author',
    'author-email',
    'maintainer',
    'maintainer-email',
    'home-page',
    'license',
    'keywords',
    'requires-python',
    'dist-name',
    'entry-points-file',
} | metadata_list_fields

metadata_required_fields = {
    'module',
    'author',
    'author-email',
    'home-page',
}

def get_cache_dir():
    if os.name == 'posix' and sys.platform != 'darwin':
        # Linux, Unix, AIX, etc.
        # use ~/.cache if empty OR not set
        xdg = os.environ.get("XDG_CACHE_HOME", None) or (os.path.expanduser('~/.cache'))
        return Path(xdg, 'flit')

    elif sys.platform == 'darwin':
        return Path(os.path.expanduser('~'), 'Library/Caches/flit')

    else:
        # Windows (hopefully)
        local = os.environ.get('LOCALAPPDATA', None) or (os.path.expanduser('~\\AppData\\Local'))
        return Path(local, 'flit')

def _verify_classifiers_cached(classifiers):
    with (get_cache_dir() / 'classifiers.lst').open() as f:
        valid_classifiers = set(l.strip() for l in f)

    invalid = classifiers - valid_classifiers
    if invalid:
        raise ConfigError("Invalid classifiers:\n" +
                          "\n".join(invalid))

def _download_classifiers():
    log.info('Fetching list of valid trove classifiers')
    resp = requests.get('https://pypi.python.org/pypi?%3Aaction=list_classifiers')
    resp.raise_for_status()

    cache_dir = get_cache_dir()
    try:
        cache_dir.mkdir(parents=True)
    except FileExistsError:
        pass
    with (get_cache_dir() / 'classifiers.lst').open('wb') as f:
        f.write(resp.content)

def verify_classifiers(classifiers):
    classifiers = set(classifiers)
    try:
        _verify_classifiers_cached(classifiers)
    except (FileNotFoundError, ConfigError):
        # FileNotFoundError: We haven't yet got the classifiers cached
        # ConfigError: At least one is invalid, but it may have been added since
        #   last time we fetched them.
        _download_classifiers()

    _verify_classifiers_cached(classifiers)


def read_pkg_ini(path):
    """Read and check the -pkg.ini file with data about the package.
    """
    cp = configparser.ConfigParser()
    with path.open() as f:
        cp.read_file(f)

    unknown_sections = set(cp.sections()) - {'metadata', 'scripts'}
    if unknown_sections:
        raise ConfigError('Unknown sections: ' + ', '.join(unknown_sections))

    if not cp.has_section('metadata'):
        raise ConfigError('[metadata] section is required')

    md_sect = cp['metadata']
    if not set(md_sect).issuperset(metadata_required_fields):
        missing = metadata_required_fields - set(md_sect)
        raise ConfigError("Required fields missing: " + '\n'.join(missing))

    module = md_sect.pop('module')
    if not module.isidentifier():
        raise ConfigError("Module name %r is not a valid identifier" % module)

    md_dict = {}

    if 'description-file' in md_sect:
        description_file = path.parent / md_sect.pop('description-file')
        with description_file.open() as f:
            md_dict['description'] = f.read()

    if 'entry-points-file' in md_sect:
        entry_points_file = path.parent / md_sect.pop('entry-points-file')
        if not entry_points_file.is_file():
            raise FileNotFoundError(entry_points_file)
    else:
        entry_points_file = path.parent / 'entry_points.txt'
        if not entry_points_file.is_file():
            entry_points_file = None

    for key, value in md_sect.items():
        if key not in metadata_allowed_fields:
            raise ConfigError("Unrecognised metadata key:", key)

        k2 = key.replace('-', '_')
        if key in metadata_list_fields:
            md_dict[k2] = value.splitlines()
        else:
            md_dict[k2] = value

    # What we call requires in the ini file is technically requires_dist in
    # the metadata.
    if 'requires' in md_dict:
        md_dict['requires_dist'] = md_dict.pop('requires')

    # And what we call dist-name is name in the metadata
    if 'dist_name' in md_dict:
        md_dict['name'] = md_dict.pop('dist_name')

    if 'classifiers' in md_dict:
        verify_classifiers(md_dict['classifiers'])

    # Scripts ---------------
    if cp.has_section('scripts'):
        scripts_dict = {k: common.parse_entry_point(v) for k, v in cp['scripts'].items()}
    else:
        scripts_dict = {}

    return {
        'module': module,
        'metadata': md_dict,
        'scripts': scripts_dict,
        'entry_points_file': entry_points_file,
    }
