import difflib
from email.headerregistry import Address
import errno
import logging
import os
import os.path as osp
from pathlib import Path
import re

try:
    import tomllib
except ImportError:
    try:
        from .vendor import tomli as tomllib
    # Some downstream distributors remove the vendored tomli.
    # When that is removed, import tomli from the regular location.
    except ImportError:
        import tomli as tomllib

from ._spdx_data import licenses
from .common import normalise_core_metadata_name
from .versionno import normalise_version

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

pep621_allowed_fields = {
    'name',
    'version',
    'description',
    'readme',
    'requires-python',
    'license',
    'license-files',
    'authors',
    'maintainers',
    'keywords',
    'classifiers',
    'urls',
    'scripts',
    'gui-scripts',
    'entry-points',
    'dependencies',
    'optional-dependencies',
    'dynamic',
}

default_license_files_globs = ['COPYING*', 'LICEN[CS]E*']
license_files_allowed_chars = re.compile(r'^[\w\-\.\/\*\?\[\]]+$')


def read_flit_config(path):
    """Read and check the `pyproject.toml` file with data about the package.
    """
    d = tomllib.loads(path.read_text('utf-8'))
    return prep_toml_config(d, path)


class EntryPointsConflict(ConfigError):
    def __str__(self):
        return ('Please specify console_scripts entry points, or [scripts] in '
            'flit config, not both.')

def prep_toml_config(d, path):
    """Validate config loaded from pyproject.toml and prepare common metadata

    Returns a LoadedConfig object.
    """
    dtool = d.get('tool', {}).get('flit', {})

    if 'project' in d:
        # Metadata in [project] table (PEP 621)
        if 'metadata' in dtool:
            raise ConfigError(
                "Use [project] table for metadata or [tool.flit.metadata], not both."
            )
        if ('scripts' in dtool) or ('entrypoints' in dtool):
            raise ConfigError(
                "Don't mix [project] metadata with [tool.flit.scripts] or "
                "[tool.flit.entrypoints]. Use [project.scripts],"
                "[project.gui-scripts] or [project.entry-points] as replacements."
            )
        loaded_cfg = read_pep621_metadata(d['project'], path)

        module_tbl = dtool.get('module', {})
        if 'name' in module_tbl:
            loaded_cfg.module = module_tbl['name']
    elif 'metadata' in dtool:
        # Metadata in [tool.flit.metadata] (pre PEP 621 format)
        if 'module' in dtool:
            raise ConfigError(
                "Use [tool.flit.module] table with new-style [project] metadata, "
                "not [tool.flit.metadata]"
            )
        loaded_cfg = _prep_metadata(dtool['metadata'], path)
        loaded_cfg.dynamic_metadata = ['version', 'description']

        if 'entrypoints' in dtool:
            loaded_cfg.entrypoints = flatten_entrypoints(dtool['entrypoints'])

        if 'scripts' in dtool:
            loaded_cfg.add_scripts(dict(dtool['scripts']))
    else:
        raise ConfigError(
            "Neither [project] nor [tool.flit.metadata] found in pyproject.toml"
        )

    unknown_sections = set(dtool) - {
        'metadata', 'module', 'scripts', 'entrypoints', 'sdist', 'external-data'
    }
    unknown_sections = [s for s in unknown_sections if not s.lower().startswith('x-')]
    if unknown_sections:
        raise ConfigError('Unexpected tables in pyproject.toml: ' + ', '.join(
            '[tool.flit.{}]'.format(s) for s in unknown_sections
        ))

    if 'sdist' in dtool:
        unknown_keys = set(dtool['sdist']) - {'include', 'exclude'}
        if unknown_keys:
            raise ConfigError(
                "Unknown keys in [tool.flit.sdist]:" + ", ".join(unknown_keys)
            )

        loaded_cfg.sdist_include_patterns = _check_glob_patterns(
            dtool['sdist'].get('include', []), 'include'
        )
        exclude = [
            "**/__pycache__",
            "**.pyc",
        ] + dtool['sdist'].get('exclude', [])
        loaded_cfg.sdist_exclude_patterns = _check_glob_patterns(
            exclude, 'exclude'
        )

    data_dir = dtool.get('external-data', {}).get('directory', None)
    if data_dir is not None:
        toml_key = "tool.flit.external-data.directory"
        if not isinstance(data_dir, str):
            raise ConfigError(f"{toml_key} must be a string")

        normp = osp.normpath(data_dir)
        if isabs_ish(normp):
            raise ConfigError(f"{toml_key} cannot be an absolute path")
        if normp.startswith('..' + os.sep):
            raise ConfigError(
                f"{toml_key} cannot point outside the directory containing pyproject.toml"
            )
        if normp == '.':
            raise ConfigError(
                f"{toml_key} cannot refer to the directory containing pyproject.toml"
            )
        loaded_cfg.data_directory = path.parent / data_dir
        if not loaded_cfg.data_directory.is_dir():
            raise ConfigError(f"{toml_key} must refer to a directory")

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

        normp = osp.normpath(p)

        if isabs_ish(normp):
            raise ConfigError(
                f'{clude} pattern {p!r} is an absolute path'
            )
        if normp.startswith('..' + os.sep):
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
        self.dynamic_metadata = []
        self.data_directory = None

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


def description_from_file(rel_path: str, proj_dir: Path, guess_mimetype=True):
    if isabs_ish(rel_path):
        raise ConfigError("Readme path must be relative")

    desc_path = proj_dir / rel_path
    try:
        with desc_path.open('r', encoding='utf-8') as f:
            raw_desc = f.read()
    except IOError as e:
        if e.errno == errno.ENOENT:
            raise ConfigError(
                "Description file {} does not exist".format(desc_path)
            )
        raise

    if guess_mimetype:
        ext = desc_path.suffix.lower()
        try:
            mimetype = readme_ext_to_content_type[ext]
        except KeyError:
            log.warning("Unknown extension %r for description file.", ext)
            log.warning("  Recognised extensions: %s",
                        " ".join(readme_ext_to_content_type))
            mimetype = None
    else:
        mimetype = None

    return raw_desc, mimetype


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
    if not all([m.isidentifier() for m in res.module.split(".")]):
        raise ConfigError("Module name %r is not a valid identifier" % res.module)

    md_dict = res.metadata

    # Description file
    if 'description-file' in md_sect:
        desc_path = md_sect.get('description-file')
        res.referenced_files.append(desc_path)
        desc_content, mimetype = description_from_file(desc_path, path.parent)
        md_dict['description'] =  desc_content
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

    reqs_extra = md_dict.pop('requires_extra', {})
    extra_names_by_normed = {}
    for e, reqs in reqs_extra.items():
        if not all(isinstance(a, str) for a in reqs):
            raise ConfigError(
                f'Expected a string list for requires-extra group {e}'
            )
        if not name_is_valid(e):
            raise ConfigError(
                f'requires-extra group name {e!r} is not valid'
            )
        enorm = normalise_core_metadata_name(e)
        extra_names_by_normed.setdefault(enorm, set()).add(e)
        res.reqs_by_extra[enorm] = reqs

    clashing_extra_names = [
        g for g in extra_names_by_normed.values() if len(g) > 1
    ]
    if clashing_extra_names:
        fmted = ['/'.join(sorted(g)) for g in clashing_extra_names]
        raise ConfigError(
            f"requires-extra group names clash: {'; '.join(fmted)}"
        )

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

    if path:
        license_files = sorted(
            _license_files_from_globs(
                path.parent, default_license_files_globs, warn_no_files=False
            )
        )
        res.referenced_files.extend(license_files)
        md_dict['license_files'] = license_files

    return res

def _expand_requires_extra(re):
    for extra, reqs in sorted(re.items()):
        for req in reqs:
            if ';' in req:
                name, envmark = req.split(';', 1)
                yield '{} ; extra == "{}" and ({})'.format(name, extra, envmark)
            else:
                yield '{} ; extra == "{}"'.format(req, extra)


def _license_files_from_globs(project_dir: Path, globs, warn_no_files = True):
    license_files = set()
    for pattern in globs:
        if isabs_ish(pattern):
            raise ConfigError(
                "Invalid glob pattern for [project.license-files]: '{}'. "
                "Pattern must not start with '/'.".format(pattern)
            )
        if ".." in pattern:
            raise ConfigError(
                "Invalid glob pattern for [project.license-files]: '{}'. "
                "Pattern must not contain '..'".format(pattern)
            )
        if license_files_allowed_chars.match(pattern) is None:
            raise ConfigError(
                "Invalid glob pattern for [project.license-files]: '{}'. "
                "Pattern contains invalid characters. "
                "https://packaging.python.org/en/latest/specifications/pyproject-toml/#license-files"
            )
        try:
            files = [
                file.relative_to(project_dir).as_posix()
                for file in project_dir.glob(pattern)
                if file.is_file()
            ]
        except ValueError as ex:
            raise ConfigError(
                "Invalid glob pattern for [project.license-files]: '{}'. {}".format(pattern, ex.args[0])
            )

        if not files and warn_no_files:
            raise ConfigError(
                "No files found for [project.license-files]: '{}' pattern".format(pattern)
            )
        license_files.update(files)
    return license_files

def _check_type(d, field_name, cls):
    if not isinstance(d[field_name], cls):
        raise ConfigError(
            "{} field should be {}, not {}".format(field_name, cls, type(d[field_name]))
        )

def _check_types(d, field_name, cls_list) -> None:
    if not isinstance(d[field_name], cls_list):
        raise ConfigError(
            "{} field should be {}, not {}".format(
                field_name, ' or '.join(map(str, cls_list)), type(d[field_name])
            )
        )

def _check_list_of_str(d, field_name):
    if not isinstance(d[field_name], list) or not all(
        isinstance(e, str) for e in d[field_name]
    ):
        raise ConfigError(
            "{} field should be a list of strings".format(field_name)
        )

def read_pep621_metadata(proj, path) -> LoadedConfig:
    lc = LoadedConfig()
    md_dict = lc.metadata

    if 'name' not in proj:
        raise ConfigError('name must be specified in [project] table')
    _check_type(proj, 'name', str)
    if not name_is_valid(proj['name']):
        raise ConfigError(f"name {proj['name']} is not valid")
    md_dict['name'] = proj['name']
    lc.module = md_dict['name'].replace('-', '_')

    unexpected_keys = proj.keys() - pep621_allowed_fields
    if unexpected_keys:
        log.warning("Unexpected names under [project]: %s", ', '.join(unexpected_keys))

    if 'version' in proj:
        _check_type(proj, 'version', str)
        md_dict['version'] = normalise_version(proj['version'])
    if 'description' in proj:
        _check_type(proj, 'description', str)
        md_dict['summary'] = proj['description']
    if 'readme' in proj:
        readme = proj['readme']
        if isinstance(readme, str):
            lc.referenced_files.append(readme)
            desc_content, mimetype = description_from_file(readme, path.parent)

        elif isinstance(readme, dict):
            unrec_keys = set(readme.keys()) - {'text', 'file', 'content-type'}
            if unrec_keys:
                raise ConfigError(
                    "Unrecognised keys in [project.readme]: {}".format(unrec_keys)
                )
            if 'content-type' in readme:
                mimetype = readme['content-type']
                mtype_base = mimetype.split(';')[0].strip()  # e.g. text/x-rst
                if mtype_base not in readme_ext_to_content_type.values():
                    raise ConfigError(
                        "Unrecognised readme content-type: {!r}".format(mtype_base)
                    )
                # TODO: validate content-type parameters (charset, md variant)?
            else:
                raise ConfigError(
                    "content-type field required in [project.readme] table"
                )
            if 'file' in readme:
                if 'text' in readme:
                    raise ConfigError(
                        "[project.readme] should specify file or text, not both"
                    )
                lc.referenced_files.append(readme['file'])
                desc_content, _ = description_from_file(
                    readme['file'], path.parent, guess_mimetype=False
                )
            elif 'text' in readme:
                desc_content = readme['text']
            else:
                raise ConfigError(
                    "file or text field required in [project.readme] table"
                )
        else:
            raise ConfigError(
                "project.readme should be a string or a table"
            )

        md_dict['description'] = desc_content
        md_dict['description_content_type'] = mimetype

    if 'requires-python' in proj:
        md_dict['requires_python'] = proj['requires-python']

    license_files = set()
    if 'license' in proj:
        _check_types(proj, 'license', (str, dict))
        if isinstance(proj['license'], str):
            licence_expr = proj['license']
            md_dict['license_expression'] = normalise_compound_license_expr(licence_expr)
        else:
            license_tbl = proj['license']
            unrec_keys = set(license_tbl.keys()) - {'text', 'file'}
            if unrec_keys:
                raise ConfigError(
                    "Unrecognised keys in [project.license]: {}".format(unrec_keys)
                )

            # The 'License' field in packaging metadata is a brief description of
            # a license, not the full text or a file path.
            if 'file' in license_tbl:
                if 'text' in license_tbl:
                    raise ConfigError(
                        "[project.license] should specify file or text, not both"
                    )
                license_f = osp.normpath(license_tbl['file'])
                if isabs_ish(license_f):
                    raise ConfigError(
                        f"License file path ({license_tbl['file']}) cannot be an absolute path"
                    )
                if license_f.startswith('..' + os.sep):
                    raise ConfigError(
                        f"License file path ({license_tbl['file']}) cannot contain '..'"
                    )
                license_p = path.parent / license_f
                if not license_p.is_file():
                    raise ConfigError(f"License file {license_tbl['file']} does not exist")
                license_f = license_p.relative_to(path.parent).as_posix()
                license_files.add(license_f)
            elif 'text' in license_tbl:
                pass
            else:
                raise ConfigError(
                    "file or text field required in [project.license] table"
                )

    if 'license-files' in proj:
        _check_type(proj, 'license-files', list)
        globs = proj['license-files']
        license_files = _license_files_from_globs(path.parent, globs)
        if isinstance(proj.get('license'), dict):
            raise ConfigError(
                "license-files cannot be used with a license table, "
                "use 'project.license' with a license expression instead"
            )
    else:
        license_files.update(
            _license_files_from_globs(
                path.parent, default_license_files_globs, warn_no_files=False
            )
        )
    license_files_sorted = sorted(license_files)
    lc.referenced_files.extend(license_files_sorted)
    md_dict['license_files'] = license_files_sorted

    if 'authors' in proj:
        _check_type(proj, 'authors', list)
        md_dict.update(pep621_people(proj['authors']))

    if 'maintainers' in proj:
        _check_type(proj, 'maintainers', list)
        md_dict.update(pep621_people(proj['maintainers'], group_name='maintainer'))

    if 'keywords' in proj:
        _check_list_of_str(proj, 'keywords')
        md_dict['keywords'] = ",".join(proj['keywords'])

    if 'classifiers' in proj:
        _check_list_of_str(proj, 'classifiers')
        classifiers = proj['classifiers']
        license_expr = md_dict.get('license_expression', None)
        if license_expr:
            for cl in classifiers:
                if not cl.startswith('License :: '):
                    continue
                raise ConfigError(
                    "License classifiers are deprecated in favor of the license expression. "
                    "Remove the '{}' classifier".format(cl)
                )
        md_dict['classifiers'] = proj['classifiers']

    if 'urls' in proj:
        _check_type(proj, 'urls', dict)
        project_urls = md_dict['project_urls'] = []
        for label, url in sorted(proj['urls'].items()):
            project_urls.append("{}, {}".format(label, url))

    if 'entry-points' in proj:
        _check_type(proj, 'entry-points', dict)
        for grp in proj['entry-points'].values():
            if not isinstance(grp, dict):
                raise ConfigError(
                    "projects.entry-points should only contain sub-tables"
                )
            if not all(isinstance(k, str) for k in grp.values()):
                raise ConfigError(
                    "[projects.entry-points.*] tables should have string values"
                )
        if set(proj['entry-points'].keys()) & {'console_scripts', 'gui_scripts'}:
            raise ConfigError(
                "Scripts should be specified in [project.scripts] or "
                "[project.gui-scripts], not under [project.entry-points]"
            )
        lc.entrypoints = proj['entry-points']

    if 'scripts' in proj:
        _check_type(proj, 'scripts', dict)
        if not all(isinstance(k, str) for k in proj['scripts'].values()):
            raise ConfigError(
                "[projects.scripts] table should have string values"
            )
        lc.entrypoints['console_scripts'] = proj['scripts']

    if 'gui-scripts' in proj:
        _check_type(proj, 'gui-scripts', dict)
        if not all(isinstance(k, str) for k in proj['gui-scripts'].values()):
            raise ConfigError(
                "[projects.gui-scripts] table should have string values"
            )
        lc.entrypoints['gui_scripts'] = proj['gui-scripts']

    if 'dependencies' in proj:
        _check_list_of_str(proj, 'dependencies')
        reqs_noextra = proj['dependencies']
    else:
        reqs_noextra = []

    if 'optional-dependencies' in proj:
        _check_type(proj, 'optional-dependencies', dict)
        optdeps = proj['optional-dependencies']
        if not all(isinstance(e, list) for e in optdeps.values()):
            raise ConfigError(
                'Expected a dict of lists in optional-dependencies field'
            )
        extra_names_by_normed = {}
        for e, reqs in optdeps.items():
            if not all(isinstance(a, str) for a in reqs):
                raise ConfigError(
                    'Expected a string list for optional-dependencies ({})'.format(e)
                )
            if not name_is_valid(e):
                raise ConfigError(
                    f'optional-dependencies group name {e!r} is not valid'
                )
            enorm = normalise_core_metadata_name(e)
            extra_names_by_normed.setdefault(enorm, set()).add(e)
            lc.reqs_by_extra[enorm] = reqs

        clashing_extra_names = [
            g for g in extra_names_by_normed.values() if len(g) > 1
        ]
        if clashing_extra_names:
            fmted = ['/'.join(sorted(g)) for g in clashing_extra_names]
            raise ConfigError(
                f"optional-dependencies group names clash: {'; '.join(fmted)}"
            )

        md_dict['provides_extra'] = sorted(lc.reqs_by_extra.keys())

    md_dict['requires_dist'] = \
        reqs_noextra + list(_expand_requires_extra(lc.reqs_by_extra))

    # For internal use, record the main requirements as a '.none' extra.
    if reqs_noextra:
        lc.reqs_by_extra['.none'] = reqs_noextra

    if 'dynamic' in proj:
        _check_list_of_str(proj, 'dynamic')
        dynamic = set(proj['dynamic'])
        unrec_dynamic = dynamic - {'version', 'description'}
        if unrec_dynamic:
            raise ConfigError(
                "flit only supports dynamic metadata for 'version' & 'description'"
            )
        if dynamic.intersection(proj):
            raise ConfigError(
                "keys listed in project.dynamic must not be in [project] table"
            )
        lc.dynamic_metadata = dynamic

    if ('version' not in proj) and ('version' not in lc.dynamic_metadata):
        raise ConfigError(
            "version must be specified under [project] or listed as a dynamic field"
        )
    if ('description' not in proj) and ('description' not in lc.dynamic_metadata):
        raise ConfigError(
            "description must be specified under [project] or listed as a dynamic field"
        )

    return lc


def name_is_valid(name) -> bool:
    return bool(re.match(
        r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", name, re.IGNORECASE
    ))


def pep621_people(people, group_name='author') -> dict:
    """Convert authors/maintainers from PEP 621 to core metadata fields"""
    names, emails = [], []
    for person in people:
        if not isinstance(person, dict):
            raise ConfigError("{} info must be list of dicts".format(group_name))
        unrec_keys = set(person.keys()) - {'name', 'email'}
        if unrec_keys:
            raise ConfigError(
                "Unrecognised keys in {} info: {}".format(group_name, unrec_keys)
            )
        if 'email' in person:
            email = person['email']
            if 'name' in person:
                email = str(Address(person['name'], addr_spec=email))
            emails.append(email)
        elif 'name' in person:
            names.append(person['name'])

    res = {}
    if names:
        res[group_name] = ", ".join(names)
    if emails:
        res[group_name + '_email'] = ", ".join(emails)
    return res


def isabs_ish(path):
    """Like os.path.isabs(), but Windows paths from a drive root count as absolute

    isabs() worked this way up to Python 3.12 (inclusive), and where we reject
    absolute paths, we also want to reject these odd halfway paths.
    """
    return os.path.isabs(path) or path.startswith(('/', '\\'))


def normalise_compound_license_expr(s: str) -> str:
    """Validate and normalise a compund SPDX license expression.

    Per the specification, licence expression operators (AND, OR and WITH)
    are matched case-sensitively. The WITH operator is not currently supported.

    Spec: https://spdx.github.io/spdx-spec/v2.2.2/SPDX-license-expressions/
    """
    invalid_msg = "'{s}' is not a valid SPDX license expression: {reason}"
    if not s or s.isspace():
        raise ConfigError(f"The SPDX license expression must not be empty")

    stack = 0
    parts = []
    try:
        for part in filter(None, re.split(r' +|([()])', s)):
            if part.upper() == 'WITH':
                # provide a sensible error message for the WITH operator
                raise ConfigError(f"The SPDX 'WITH' operator is not yet supported!")
            elif part in {'AND', 'OR'}:
                if not parts or parts[-1] in {' AND ', ' OR ', ' WITH ', '('}:
                    reason = f"a license ID is missing before '{part}'"
                    raise ConfigError(invalid_msg.format(s=s, reason=reason))
                parts.append(f' {part} ')
            elif part.lower() in {'and', 'or', 'with'}:
                # provide a sensible error message for non-uppercase operators
                reason = f"operators must be uppercase, not '{part}'"
                raise ConfigError(invalid_msg.format(s=s, reason=reason))
            elif part == '(':
                if parts and parts[-1] not in {' AND ', ' OR ', '('}:
                    reason = f"'(' must follow either AND, OR, or '('"
                    raise ConfigError(invalid_msg.format(s=s, reason=reason))
                stack += 1
                parts.append(part)
            elif part == ')':
                if not parts or parts[-1] in {' AND ', ' OR ', ' WITH ', '('}:
                    reason = f"a license ID is missing before '{part}'"
                    raise ConfigError(invalid_msg.format(s=s, reason=reason))
                stack -= 1
                if stack < 0:
                    reason = 'unbalanced brackets'
                    raise ConfigError(invalid_msg.format(s=s, reason=reason))
                parts.append(part)
            else:
                if parts and parts[-1] not in {' AND ', ' OR ', '('}:
                    reason = f"a license ID must follow either AND, OR, or '('"
                    raise ConfigError(invalid_msg.format(s=s, reason=reason))
                simple_expr = normalise_simple_license_expr(part)
                parts.append(simple_expr)

        if stack != 0:
            reason = 'unbalanced brackets'
            raise ConfigError(invalid_msg.format(s=s, reason=reason))
        if parts[-1] in {' AND ', ' OR ', ' WITH '}:
            last_part = parts[-1].strip()
            reason = f"a license ID or expression should follow '{last_part}'"
            raise ConfigError(invalid_msg.format(s=s, reason=reason))
    except ConfigError:
        if os.environ.get('FLIT_ALLOW_INVALID'):
            log.warning(f"Invalid license ID {s!r} allowed by FLIT_ALLOW_INVALID")
            return s
        raise

    return ''.join(parts)


def normalise_simple_license_expr(s: str) -> str:
    """Normalise a simple SPDX license expression.

    https://spdx.github.io/spdx-spec/v2.2.2/SPDX-license-expressions/#d3-simple-license-expressions
    """
    ls = s.lower()
    if ls.startswith('licenseref-'):
        ref = s[11:]
        if re.fullmatch(r'[a-zA-Z0-9\-.]+', ref):
            # Normalise case of LicenseRef, leave the rest alone
            return f"LicenseRef-{ref}"
        raise ConfigError(
            "LicenseRef- license expression can only contain ASCII letters "
            "& digits, - and ."
        )

    or_later = ls.endswith('+')
    if or_later:
        ls = ls[:-1]

    try:
        normalised_id = licenses[ls]['id']
    except KeyError:
        raise ConfigError(f"{s!r} is not a recognised SPDX license ID")

    if or_later:
        return f'{normalised_id}+'
    return normalised_id
