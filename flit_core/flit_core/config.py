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
    'import-names',  # PEP 794
    'import-namespaces'
}

allowed_dynamic_fields = {
    'version',
    'description',
    'import-names',
    'import-namespaces'
}


default_license_files_globs = ['COPYING*', 'LICEN[CS]E*', 'NOTICE*', 'AUTHORS*']
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

    if 'metadata' in dtool:
        raise ConfigError(
            "The [tool.flit.metadata] table is no longer supported. "
            "Switch to the standard [project] table or require flit_core<4 "
            "to build this package."
        )
    if ('scripts' in dtool) or ('entrypoints' in dtool):
        raise ConfigError(
            "The [tool.flit.scripts] and [tool.flit.entrypoints] tables are no "
            "longer supported. Use [project.scripts], [project.gui-scripts] or"
            "[project.entry-points] as replacements."
        )

    if 'project' not in d:
        raise ConfigError("No [project] table found in pyproject.toml")

    loaded_cfg = read_pep621_metadata(d['project'], path)

    module_tbl = dtool.get('module', {})
    if 'name' in module_tbl:
        loaded_cfg.module = module_tbl['name']

    if 'import-names' in d['project']:
        import_names_from_config = [
            s.split(';')[0] for s in loaded_cfg.metadata['import_name']
        ]
        if import_names_from_config != [loaded_cfg.module]:
            raise ConfigError(
                f"Specified import-names {import_names_from_config} do not match "
                f"the module present ({loaded_cfg.module})"
            )
    else:
        loaded_cfg.metadata['import_name'] = [loaded_cfg.module]

    namespace_parts = loaded_cfg.module.split('.')[:-1]
    nspkgs_from_mod_name = [
        '.'.join(namespace_parts[:i]) for i in range(1, len(namespace_parts) + 1)
    ]
    if 'import-namespaces' in d['project']:
        nspkgs_from_config = [
            s.split(';')[0] for s in loaded_cfg.metadata['import_namespace']
        ]
        if set(nspkgs_from_config) != set(nspkgs_from_mod_name):
            raise ConfigError(
                f"Specified import-namespaces {nspkgs_from_config} do not match "
                f"the namespace packages present ({nspkgs_from_mod_name})"
            )
    else:
        loaded_cfg.metadata['import_namespace'] = nspkgs_from_mod_name

    unknown_sections = set(dtool) - {'module', 'sdist', 'external-data'}
    unknown_sections = [s for s in unknown_sections if not s.lower().startswith('x-')]
    if unknown_sections:
        raise ConfigError('Unexpected tables in pyproject.toml: ' + ', '.join(
            f'[tool.flit.{s}]' for s in unknown_sections
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


def _check_glob_patterns(pats, clude):
    """Check and normalise glob patterns for sdist include/exclude"""
    if not isinstance(pats, list):
        raise ConfigError(f"sdist {clude} patterns must be a list")

    # Windows filenames can't contain these (nor * or ?, but they are part of
    # glob patterns) - https://stackoverflow.com/a/31976060/434217
    bad_chars = re.compile(r'[\000-\037<>:"\\]')

    normed = []

    for p in pats:
        if bad_chars.search(p):
            raise ConfigError(
                f'{clude} pattern {p!r} contains bad characters (<>:\"\\ or control characters)'
            )

        normp = osp.normpath(p)

        if isabs_ish(normp):
            raise ConfigError(
                f'{clude} pattern {p!r} is an absolute path'
            )
        if normp.startswith('..' + os.sep):
            raise ConfigError(
                f'{clude} pattern {p!r} points out of the directory containing pyproject.toml'
            )
        normed.append(normp)

    return normed


class LoadedConfig:
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
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise ConfigError(
                f"Description file {desc_path} does not exist"
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


def _expand_requires_extra(re):
    for extra, reqs in sorted(re.items()):
        for req in reqs:
            if ';' in req:
                name, envmark = req.split(';', 1)
                yield f'{name} ; extra == "{extra}" and ({envmark})'
            else:
                yield f'{req} ; extra == "{extra}"'


def _license_files_from_globs(project_dir: Path, globs, warn_no_files = True):
    license_files = set()
    for pattern in globs:
        if isabs_ish(pattern):
            raise ConfigError(
                f"Invalid glob pattern for [project.license-files]: '{pattern}'. "
                "Pattern must not start with '/'."
            )
        if ".." in pattern:
            raise ConfigError(
                f"Invalid glob pattern for [project.license-files]: '{pattern}'. "
                "Pattern must not contain '..'"
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
                f"Invalid glob pattern for [project.license-files]: '{pattern}'. {ex.args[0]}"
            )

        if not files and warn_no_files:
            raise ConfigError(
                f"No files found for [project.license-files]: '{pattern}' pattern"
            )
        license_files.update(files)
    return license_files

def _check_type(d, field_name, cls):
    if not isinstance(d[field_name], cls):
        raise ConfigError(
            f"{field_name} field should be {cls}, not {type(d[field_name])}"
        )

def _check_types(d, field_name, cls_list) -> None:
    if not isinstance(d[field_name], cls_list):
        cls_str = ' or '.join(map(str, cls_list))
        raise ConfigError(
            f"{field_name} field should be {cls_str}, not {type(d[field_name])}"
        )

def _check_list_of_str(d, field_name):
    if not isinstance(d[field_name], list) or not all(
        isinstance(e, str) for e in d[field_name]
    ):
        raise ConfigError(
            f"{field_name} field should be a list of strings"
        )

def normalize_pkg_name(name: str) -> str:
    if name.endswith('-stubs'):
        # TODO: use `str.removesuffix` after we drop py3.8
        return name[:-6].replace('-','_') + '-stubs'
    return name.replace('-','_')


def normalize_import_name(name: str) -> str:
    if ';' in name:
        name, annotation = name.split(';', 1)
        name = name.rstrip()
        annotation = annotation.lstrip()
        if annotation != 'private':
            raise ConfigError(
                f"{annotation!r} for import name {name!r} is not allowed "
                "(the only valid annotation is 'private')"
            )
    else:
        annotation = None

    if not all(p.isidentifier() for p in name.split('.')):
        raise ConfigError(f"{name!r} is not a valid import name")

    return f"{name}; {annotation}" if annotation else name


def read_pep621_metadata(proj, path) -> LoadedConfig:
    lc = LoadedConfig()
    md_dict = lc.metadata

    if 'name' not in proj:
        raise ConfigError('name must be specified in [project] table')
    _check_type(proj, 'name', str)
    if not name_is_valid(proj['name']):
        raise ConfigError(f"name {proj['name']} is not valid")
    md_dict['name'] = proj['name']
    lc.module = normalize_pkg_name(md_dict['name'])

    unexpected_keys = proj.keys() - pep621_allowed_fields
    if unexpected_keys:
        raise ConfigError(
            "Unrecognised key(s) in [project] table: " + ', '.join(unexpected_keys)
        )

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
                    f"Unrecognised keys in [project.readme]: {unrec_keys}"
                )
            if 'content-type' in readme:
                mimetype = readme['content-type']
                mtype_base = mimetype.split(';')[0].strip()  # e.g. text/x-rst
                if mtype_base not in readme_ext_to_content_type.values():
                    raise ConfigError(
                        f"Unrecognised readme content-type: {mtype_base!r}"
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
                    f"Unrecognised keys in [project.license]: {unrec_keys}"
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
                    f"Remove the '{cl}' classifier"
                )
        md_dict['classifiers'] = proj['classifiers']

    if 'urls' in proj:
        _check_type(proj, 'urls', dict)
        project_urls = md_dict['project_urls'] = []
        for label, url in sorted(proj['urls'].items()):
            project_urls.append(f"{label}, {url}")

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
                    f'Expected a string list for optional-dependencies ({e})'
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

    if 'import-names' in proj:  # PEP 794
        _check_list_of_str(proj, 'import-names')
        md_dict['import_name'] = [
            normalize_import_name(s) for s in proj['import-names']
        ]

    if 'import-namespaces' in proj:
        _check_list_of_str(proj, 'import-namespaces')
        md_dict['import_namespace'] = [
            normalize_import_name(s) for s in proj['import-namespaces']
        ]

    if 'dynamic' in proj:
        _check_list_of_str(proj, 'dynamic')
        dynamic = set(proj['dynamic'])
        unrec_dynamic = dynamic - allowed_dynamic_fields
        if unrec_dynamic:
            raise ConfigError(
                "flit only supports dynamic metadata for:" + ', '.join(
                    sorted(allowed_dynamic_fields)
                )
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
            raise ConfigError(f"{group_name} info must be list of dicts")
        unrec_keys = set(person.keys()) - {'name', 'email'}
        if unrec_keys:
            raise ConfigError(
                f"Unrecognised keys in {group_name} info: {unrec_keys}"
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
        raise ConfigError("The SPDX license expression must not be empty")

    stack = 0
    parts = []
    try:
        for part in filter(None, re.split(r' +|([()])', s)):
            if part.upper() == 'WITH':
                # provide a sensible error message for the WITH operator
                raise ConfigError("The SPDX 'WITH' operator is not yet supported!")
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
                    reason = "'(' must follow either AND, OR, or '('"
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
                    reason = "a license ID must follow either AND, OR, or '('"
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
            log.warning("Invalid license ID %r allowed by FLIT_ALLOW_INVALID", s)
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
