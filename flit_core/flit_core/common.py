import ast
from contextlib import contextmanager
import hashlib
import logging
import os
import sys

from pathlib import Path
import re

log = logging.getLogger(__name__)

from .versionno import normalise_version

class Module:
    """This represents the module/package that we are going to distribute
    """
    in_namespace_package = False
    namespace_package_name = None

    def __init__(self, name: str, directory=Path()):
        self.name = name
        self.is_stub_pkg = name.endswith('-stubs')

        # It must exist either as a .py file or a directory, but not both
        name_as_path = name.replace('.', os.sep)
        pkg_dir = directory / name_as_path
        py_file = directory / (name_as_path+'.py')
        src_pkg_dir = directory / 'src' / name_as_path
        src_py_file = directory / 'src' / (name_as_path+'.py')

        existing = set()
        if pkg_dir.is_dir():
            self.path = pkg_dir
            self.is_package = True
            self.prefix = ''
            existing.add(pkg_dir)
        if py_file.is_file():
            self.path = py_file
            self.is_package = False
            self.prefix = ''
            existing.add(py_file)
        if src_pkg_dir.is_dir():
            self.path = src_pkg_dir
            self.is_package = True
            self.prefix = 'src'
            existing.add(src_pkg_dir)
        if src_py_file.is_file():
            self.path = src_py_file
            self.is_package = False
            self.prefix = 'src'
            existing.add(src_py_file)

        if len(existing) > 1:
            existing_str = ", ".join(map(str, sorted(existing)))
            raise ValueError(
                f"Multiple files or folders could be module {name}: {existing_str}"
            )
        elif not existing:
            raise ValueError(f"No file/folder found for module {name}")

        self.source_dir = directory / self.prefix

        if '.' in name:
            self.namespace_package_name = name.rpartition('.')[0]
            self.in_namespace_package = True

    @property
    def file(self):
        if self.is_package:
            return self.path / '__init__.py'
        else:
            return self.path

    @property
    def version_files(self):
        """Files which will be parsed to find a version number

        Files later in this list take precedence over earlier ones.
        """
        if self.is_package:
            paths = [self.path / '__init__.py']
            for filename in ('version.py', '_version.py', '__version__.py'):
                if (self.path / filename).is_file():
                    paths.insert(0, self.path / filename)
            return paths
        else:
            return [self.path]

    def iter_files(self):
        """Iterate over the files contained in this module.

        Yields absolute paths - caller may want to make them relative.
        Excludes any __pycache__ and *.pyc files.
        """
        def _include(path):
            name = os.path.basename(path)
            return name != '__pycache__' and not name.endswith('.pyc')

        if self.is_package:
            # Ensure we sort all files and directories so the order is stable
            for dirpath, dirs, files in os.walk(str(self.path)):
                for file in sorted(files):
                    full_path = os.path.join(dirpath, file)
                    if _include(full_path):
                        yield full_path

                dirs[:] = [d for d in sorted(dirs) if _include(d)]

        else:
            yield str(self.path)

class ProblemInModule(ValueError): pass
class NoDocstringError(ProblemInModule): pass
class NoVersionError(ProblemInModule): pass
class InvalidVersion(ProblemInModule): pass

class VCSError(Exception):
    def __init__(self, msg, directory):
        self.msg = msg
        self.directory = directory

    def __str__(self):
        return f'{self.msg} ({self.directory})'


@contextmanager
def _module_load_ctx():
    """Preserve some global state that modules might change at import time.

    - Handlers on the root logger.
    """
    logging_handlers = logging.root.handlers[:]
    try:
        yield
    finally:
        logging.root.handlers = logging_handlers

def get_docstring_and_version_via_ast(target):
    """
    Return a tuple like (docstring, version) for the given module,
    extracted by parsing its AST.
    """
    version = None
    for target_path in target.version_files:
        # read as bytes to enable custom encodings
        with target_path.open('rb') as f:
            node = ast.parse(f.read())
        for child in node.body:
            if is_version_str_assignment(child):
                version = child.value.value
                break
    return ast.get_docstring(node), version


def is_version_str_assignment(node):
    """Check if *node* is a simple string assignment to __version__"""
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        return False
    if not isinstance(node.value, ast.Constant):
        return False
    targets = (node.target,) if isinstance(node, ast.AnnAssign) else node.targets
    for target in targets:
        if isinstance(target, ast.Name) and target.id == "__version__":
            return True
    return False


# To ensure we're actually loading the specified file, give it a unique name to
# avoid any cached import. In normal use we'll only load one module per process,
# so it should only matter for the tests, but we'll do it anyway.
_import_i = 0


def get_docstring_and_version_via_import(target):
    """
    Return a tuple like (docstring, version) for the given module,
    extracted by importing the module and pulling __doc__ & __version__
    from it.
    """
    global _import_i
    _import_i += 1

    log.debug("Loading module %s", target.file)
    from importlib.util import spec_from_file_location, module_from_spec
    mod_name = f'flit_core.dummy.import{_import_i}'
    spec = spec_from_file_location(mod_name, target.file)
    with _module_load_ctx():
        m = module_from_spec(spec)
        # Add the module to sys.modules to allow relative imports to work.
        # importlib has more code around this to handle the case where two
        # threads are trying to load the same module at the same time, but Flit
        # should always be running a single thread, so we won't duplicate that.
        sys.modules[mod_name] = m
        try:
            spec.loader.exec_module(m)
        finally:
            sys.modules.pop(mod_name, None)

    docstring = m.__dict__.get('__doc__', None)
    version = m.__dict__.get('__version__', None)
    return docstring, version


def get_info_from_module(target, for_fields=('version', 'description')):
    """Load the module/package, get its docstring and __version__
    """
    if not for_fields:
        return {}

    # What core metadata calls Summary, PEP 621 calls description
    want_summary = 'description' in for_fields
    want_version = 'version' in for_fields

    log.debug("Loading module %s", target.file)

    # Attempt to extract our docstring & version by parsing our target's
    # AST, falling back to an import if that fails. This allows us to
    # build without necessarily requiring that our built package's
    # requirements are installed.
    docstring, version = get_docstring_and_version_via_ast(target)
    if (want_summary and not docstring) or (want_version and not version):
        docstring, version = get_docstring_and_version_via_import(target)

    res = {}

    if want_summary:
        if (not docstring) or not docstring.strip():
            raise NoDocstringError(
                'Flit cannot package module without docstring, or empty docstring. '
                f'Please add a docstring to your module ({target.file}).'
            )
        res['summary'] = docstring.lstrip().splitlines()[0]

    if want_version:
        res['version'] = check_version(version)

    return res

def check_version(version):
    """
    Check whether a given version string match PEP 440, and do normalisation.

    Raise InvalidVersion/NoVersionError with relevant information if
    version is invalid.

    Log a warning if the version is not canonical with respect to PEP 440.

    Returns the version in canonical PEP 440 format.
    """
    if not version:
        raise NoVersionError('Cannot package module without a version string. '
                             'Please define a `__version__ = "x.y.z"` in your module.')
    if not isinstance(version, str):
        raise InvalidVersion(f'__version__ must be a string, not {type(version)}.')

    # Import here to avoid circular import
    version = normalise_version(version)

    return version


script_template = """\
#!{interpreter}
# -*- coding: utf-8 -*-
import re
import sys
from {module} import {import_name}
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?$', '', sys.argv[0])
    sys.exit({func}())
"""

def parse_entry_point(ep):
    """Check and parse a 'package.module:func' style entry point specification.

    Returns (modulename, funcname)
    """
    if ':' not in ep:
        raise ValueError(f"Invalid entry point (no ':'): {ep!r}")
    mod, func = ep.split(':')

    for piece in func.split('.'):
        if not piece.isidentifier():
            raise ValueError(f"Invalid entry point: {piece!r} is not an identifier")
    for piece in mod.split('.'):
        if not piece.isidentifier():
            raise ValueError(f"Invalid entry point: {piece!r} is not a module path")

    return mod, func

def write_entry_points(d, fp):
    """Write entry_points.txt from a two-level dict

    Sorts on keys to ensure results are reproducible.
    """
    for group_name in sorted(d):
        fp.write(f'[{group_name}]\n')
        group = d[group_name]
        for name in sorted(group):
            val = group[name]
            fp.write(f'{name}={val}\n')
        fp.write('\n')

def hash_file(path, algorithm='sha256'):
    with open(path, 'rb') as f:
        h = hashlib.new(algorithm, f.read())
    return h.hexdigest()

def normalize_file_permissions(st_mode):
    """Normalize the permission bits in the st_mode field from stat to 644/755

    Popular VCSs only track whether a file is executable or not. The exact
    permissions can vary on systems with different umasks. Normalising
    to 644 (non executable) or 755 (executable) makes builds more reproducible.
    """
    # Set 644 permissions, leaving higher bits of st_mode unchanged
    new_mode = (st_mode | 0o644) & ~0o133
    if st_mode & 0o100:
        new_mode |= 0o111  # Executable: 644 -> 755
    return new_mode

class Metadata:

    summary = None
    home_page = None
    author = None
    author_email = None
    maintainer = None
    maintainer_email = None
    license = None
    license_expression = None
    description = None
    keywords = None
    download_url = None
    requires_python = None
    description_content_type = None

    platform = ()
    supported_platform = ()
    classifiers = ()
    provides = ()
    requires = ()
    obsoletes = ()
    project_urls = ()
    provides_dist = ()
    requires_dist = ()
    obsoletes_dist = ()
    requires_external = ()
    provides_extra = ()
    license_files = ()
    dynamic = ()

    metadata_version = "2.4"

    def __init__(self, data):
        data = data.copy()
        self.name = data.pop('name')
        self.version = data.pop('version')

        for k, v in data.items():
            assert hasattr(self, k), f"data does not have attribute '{k}'"
            setattr(self, k, v)

    def _normalise_field_name(self, n):
        return n.lower().replace('-', '_')

    def _extract_extras(self, req):
        match = re.search(r'\[([^]]*)\]', req)
        if match:
            list_str = match.group(1)
            return [item.strip() for item in list_str.split(',')]
        else:
            return None

    def _normalise_requires_dist(self, req):
        extras = self._extract_extras(req)
        if extras:
            normalised_extras = [normalise_core_metadata_name(extra) for extra in extras]
            normalised_extras_str = ', '.join(normalised_extras)
            normalised_req = re.sub(r'\[([^]]*)\]', f"[{normalised_extras_str}]", req)
            return normalised_req
        else:
            return req

    def write_metadata_file(self, fp):
        """Write out metadata in the email headers format"""
        fields = [
            'Metadata-Version',
            'Name',
            'Version',
        ]
        optional_fields = [
            'Summary',
            'Home-page',
            'Keywords',
            'Author',
            'Author-email',
            'Maintainer',
            'Maintainer-email',
            'Requires-Python',
            'Description-Content-Type',
        ]

        for field in fields:
            value = getattr(self, self._normalise_field_name(field))
            fp.write(f"{field}: {value}\n")

        for field in optional_fields:
            value = getattr(self, self._normalise_field_name(field))
            if value is not None:
                # TODO: verify which fields can be multiline
                # The spec has multiline examples for Author, Maintainer &
                # License (& Description, but we put that in the body)
                # Indent following lines with 8 spaces:
                value = '\n        '.join(value.splitlines())
                fp.write(f"{field}: {value}\n")


        license_expr = getattr(self, self._normalise_field_name("License-Expression"))
        license = getattr(self, self._normalise_field_name("License"))
        if license_expr:
            fp.write(f'License-Expression: {license_expr}\n')
        elif license:  # Deprecated, superseded by License-Expression
            fp.write(f'License: {license}\n')

        for clsfr in self.classifiers:
            fp.write(f'Classifier: {clsfr}\n')

        for file in self.license_files:
            fp.write(f'License-File: {file}\n')

        for req in self.requires_dist:
            normalised_req = self._normalise_requires_dist(req)
            fp.write(f'Requires-Dist: {normalised_req}\n')

        for url in self.project_urls:
            fp.write(f'Project-URL: {url}\n')

        for extra in self.provides_extra:
            normalised_extra = normalise_core_metadata_name(extra)
            fp.write(f'Provides-Extra: {normalised_extra}\n')

        if self.description is not None:
            fp.write(f'\n{self.description}\n')

    @property
    def supports_py2(self):
        """Return True if Requires-Python indicates Python 2 support."""
        for part in (self.requires_python or "").split(","):
            if re.search(r"^\s*(>=?|~=|===?)?\s*[3-9]", part):
                return False
        return True


def make_metadata(module, ini_info):
    md_dict = {'name': module.name, 'provides': [module.name]}
    md_dict.update(get_info_from_module(module, ini_info.dynamic_metadata))
    md_dict.update(ini_info.metadata)
    return Metadata(md_dict)


def normalise_core_metadata_name(name):
    """Normalise a project or extra name (as in PEP 503, also PEP 685)"""
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_dist_name(name: str, version: str) -> str:
    """Normalizes a name and a PEP 440 version

    The resulting string is valid as dist-info folder name
    and as first part of a wheel filename

    See https://packaging.python.org/specifications/binary-distribution-format/#escaping-and-unicode
    """
    normalized_name = re.sub(r'[-_.]+', '_', name, flags=re.UNICODE).lower()
    assert check_version(version) == version
    assert '-' not in version, 'Normalized versions can’t have dashes'
    return f'{normalized_name}-{version}'


def dist_info_name(distribution, version):
    """Get the correct name of the .dist-info folder"""
    return f'{normalize_dist_name(distribution, version)}.dist-info'


def walk_data_dir(data_directory):
    """Iterate over the files in the given data directory.

    Yields paths prefixed with data_directory - caller may want to make them
    relative to that. Excludes any __pycache__ subdirectories.
    """
    if data_directory is None:
        return

    for dirpath, dirs, files in os.walk(data_directory):
        for file in sorted(files):
            full_path = os.path.join(dirpath, file)
            yield full_path

        dirs[:] = [d for d in sorted(dirs) if d != '__pycache__']
