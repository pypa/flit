import difflib
import errno
import logging
import os
import os.path as osp
import toml
import re

log = logging.getLogger(__name__)


class ConfigError(ValueError):
    pass

metadata_list_fields = {
    'classifiers',
    'requires',
    'dev-requires'
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
    'description-file',
    'requires-extra',
} | metadata_list_fields

metadata_required_fields = {
    'module',
    'author',
}


def read_flit_config(path):
    """Read and check the `pyproject.toml` file with data about the package.
    """
    with path.open('r', encoding='utf-8') as f:
        d = toml.load(f)
    return prep_toml_config(d, path)


class EntryPointsConflict(ConfigError):
    def __str__(self):
        return ('Please specify console_scripts entry points, or [scripts] in '
            'flit config, not both.')

def prep_toml_config(d, path):
    """Validate config loaded from pyproject.toml and prepare common metadata
    
    Returns a LoadedConfig object.
    """
    if ('tool' not in d) or ('flit' not in d['tool']) \
            or (not isinstance(d['tool']['flit'], dict)):
        raise ConfigError("TOML file missing [tool.flit] table.")

    d = d['tool']['flit']
    unknown_sections = set(d) - {'metadata', 'scripts', 'entrypoints', 'sdist'}
    unknown_sections = [s for s in unknown_sections if not s.lower().startswith('x-')]
    if unknown_sections:
        raise ConfigError('Unknown sections: ' + ', '.join(unknown_sections))

    if 'metadata' not in d:
        raise ConfigError('[tool.flit.metadata] section is required')

    loaded_cfg = _prep_metadata(d['metadata'], path)

    if 'entrypoints' in d:
        loaded_cfg.entrypoints = flatten_entrypoints(d['entrypoints'])

    if 'scripts' in d:
        loaded_cfg.add_scripts(dict(d['scripts']))

    if 'sdist' in d:
        unknown_keys = set(d['sdist']) - {'include', 'exclude'}
        if unknown_keys:
            raise ConfigError(
                "Unknown keys in [tool.flit.sdist]:" + ", ".join(unknown_keys)
            )

        loaded_cfg.sdist_include_patterns = _check_glob_patterns(
            d['sdist'].get('include', []), 'include'
        )
        loaded_cfg.sdist_exclude_patterns = _check_glob_patterns(
            d['sdist'].get('exclude', []), 'exclude'
        )

    return loaded_cfg

def flatten_entrypoints(ep):
    """Flatten nested entrypoints dicts.

    Entry points group names can include dots. But dots in TOML make nested
    dictionaries:

    [entrypoints.a.b]    # {'entrypoints': {'a': {'b': {}}}}

    The proper way to avoid this is:

    [entrypoints."a.b"]  # {'entrypoints': {'a.b': {}}}

    But since there isn't a need for arbitrarily nested mappings in entrypoints,
    flit allows you to use the former. This flattens the nested dictionaries
    from loading pyproject.toml.
    """
    def _flatten(d, prefix):
        d1 = {}
        for k, v in d.items():
            if isinstance(v, dict):
                for flattened in _flatten(v, prefix+'.'+k):
                    yield flattened
            else:
                d1[k] = v

        if d1:
            yield prefix, d1

    res = {}
    for k, v in ep.items():
        res.update(_flatten(v, k))
    return res


def _check_glob_patterns(pats, clude):
    """Check and normalise glob patterns for sdist include/exclude"""
    if not isinstance(pats, list):
        raise ConfigError("sdist {} patterns must be a list".format(clude))

    # Windows filenames can't contain these (nor * or ?, but they are part of
    # glob patterns) - https://stackoverflow.com/a/31976060/434217
    bad_chars = re.compile(r'[\000-\037<>:"\\]')

    normed = []

    for p in pats:
        if bad_chars.search(p):
            raise ConfigError(
                '{} pattern {!r} contains bad characters (<>:\"\\ or control characters)'
                .format(clude, p)
            )
        if '**' in p:
            raise ConfigError(
                "Recursive globbing (**) is not supported yet (in {} pattern {!r})"
                .format(clude, p)
            )

        normp = osp.normpath(p)

        if osp.isabs(normp):
            raise ConfigError(
                '{} pattern {!r} is an absolute path'.format(clude, p)
            )
        if osp.normpath(p).startswith('..' + os.sep):
            raise ConfigError(
                '{} pattern {!r} points out of the directory containing pyproject.toml'
                .format(clude, p)
            )
        normed.append(normp)

    return normed


class LoadedConfig(object):
    def __init__(self):
        self.module = None
        self.metadata = {}
        self.reqs_by_extra = {}
        self.entrypoints = {}
        self.referenced_files = []
        self.sdist_include_patterns = []
        self.sdist_exclude_patterns = []

    def add_scripts(self, scripts_dict):
        if scripts_dict:
            if 'console_scripts' in self.entrypoints:
                raise EntryPointsConflict
            else:
                self.entrypoints['console_scripts'] = scripts_dict

readme_ext_to_content_type = {
    '.rst': 'text/x-rst',
    '.md': 'text/markdown',
    '.txt': 'text/plain',
}


def _prep_metadata(md_sect, path):
    """Process & verify the metadata from a config file
    
    - Pull out the module name we're packaging.
    - Read description-file and check that it's valid rst
    - Convert dashes in key names to underscores
      (e.g. home-page in config -> home_page in metadata) 
    """
    if not set(md_sect).issuperset(metadata_required_fields):
        missing = metadata_required_fields - set(md_sect)
        raise ConfigError("Required fields missing: " + '\n'.join(missing))

    res = LoadedConfig()

    res.module = md_sect.get('module')
    if not str.isidentifier(res.module):
        raise ConfigError("Module name %r is not a valid identifier" % res.module)

    md_dict = res.metadata

    # Description file
    if 'description-file' in md_sect:
        desc_path = md_sect.get('description-file')
        res.referenced_files.append(desc_path)
        description_file = path.parent / desc_path
        try:
            with description_file.open('r', encoding='utf-8') as f:
                raw_desc = f.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise ConfigError(
                    "Description file {} does not exist".format(description_file)
                )
            raise
        ext = description_file.suffix
        try:
            mimetype = readme_ext_to_content_type[ext]
        except KeyError:
            log.warning("Unknown extension %r for description file.", ext)
            log.warning("  Recognised extensions: %s",
                        " ".join(readme_ext_to_content_type))
            mimetype = None

        md_dict['description'] =  raw_desc
        md_dict['description_content_type'] = mimetype

    if 'urls' in md_sect:
        project_urls = md_dict['project_urls'] = []
        for label, url in sorted(md_sect.pop('urls').items()):
            project_urls.append("{}, {}".format(label, url))

    for key, value in md_sect.items():
        if key in {'description-file', 'module'}:
            continue
        if key not in metadata_allowed_fields:
            closest = difflib.get_close_matches(key, metadata_allowed_fields,
                                                n=1, cutoff=0.7)
            msg = "Unrecognised metadata key: {!r}".format(key)
            if closest:
                msg += " (did you mean {!r}?)".format(closest[0])
            raise ConfigError(msg)

        k2 = key.replace('-', '_')
        md_dict[k2] = value
        if key in metadata_list_fields:
            if not isinstance(value, list):
                raise ConfigError('Expected a list for {} field, found {!r}'
                                    .format(key, value))
            if not all(isinstance(a, str) for a in value):
                raise ConfigError('Expected a list of strings for {} field'
                                    .format(key))
        elif key == 'requires-extra':
            if not isinstance(value, dict):
                raise ConfigError('Expected a dict for requires-extra field, found {!r}'
                                    .format(value))
            if not all(isinstance(e, list) for e in value.values()):
                raise ConfigError('Expected a dict of lists for requires-extra field')
            for e, reqs in value.items():
                if not all(isinstance(a, str) for a in reqs):
                    raise ConfigError('Expected a string list for requires-extra. (extra {})'
                                        .format(e))
        else:
            if not isinstance(value, str):
                raise ConfigError('Expected a string for {} field, found {!r}'
                                    .format(key, value))

    # What we call requires in the ini file is technically requires_dist in
    # the metadata.
    if 'requires' in md_dict:
        md_dict['requires_dist'] = md_dict.pop('requires')

    # And what we call dist-name is name in the metadata
    if 'dist_name' in md_dict:
        md_dict['name'] = md_dict.pop('dist_name')

    # Move dev-requires into requires-extra
    reqs_noextra = md_dict.pop('requires_dist', [])
    res.reqs_by_extra = md_dict.pop('requires_extra', {})
    dev_requires = md_dict.pop('dev_requires', None)
    if dev_requires is not None:
        if 'dev' in res.reqs_by_extra:
            raise ConfigError(
                'dev-requires occurs together with its replacement requires-extra.dev.')
        else:
            log.warning(
                '"dev-requires = ..." is obsolete. Use "requires-extra = {"dev" = ...}" instead.')
            res.reqs_by_extra['dev'] = dev_requires

    # Add requires-extra requirements into requires_dist
    md_dict['requires_dist'] = \
        reqs_noextra + list(_expand_requires_extra(res.reqs_by_extra))

    md_dict['provides_extra'] = sorted(res.reqs_by_extra.keys())

    # For internal use, record the main requirements as a '.none' extra.
    res.reqs_by_extra['.none'] = reqs_noextra

    return res

def _expand_requires_extra(re):
    for extra, reqs in sorted(re.items()):
        for req in reqs:
            if ';' in req:
                name, envmark = req.split(';', 1)
                yield '{} ; extra == "{}" and ({})'.format(name, extra, envmark)
            else:
                yield '{} ; extra == "{}"'.format(req, extra)
