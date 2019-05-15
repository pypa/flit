import ast
from contextlib import contextmanager
import hashlib
from importlib.machinery import SourceFileLoader
import logging
from pathlib import Path
import re

log = logging.getLogger(__name__)

import re

class Module(object):
    """This represents the module/package that we are going to distribute
    """
    def __init__(self, name, directory='.'):
        self.name = name

        # It must exist either as a .py file or a directory, but not both
        pkg_dir = Path(directory, name)
        py_file = Path(directory, name+'.py')
        if pkg_dir.is_dir() and py_file.is_file():
            raise ValueError("Both {} and {} exist".format(pkg_dir, py_file))
        elif pkg_dir.is_dir():
            self.path = pkg_dir
            self.is_package = True
        elif py_file.is_file():
            self.path = py_file
            self.is_package = False
        else:
            raise ValueError("No file/folder found for module {}".format(name))

    @property
    def file(self):
        if self.is_package:
            return self.path / '__init__.py'
        else:
            return self.path

class ProblemInModule(ValueError): pass
class NoDocstringError(ProblemInModule): pass
class NoVersionError(ProblemInModule): pass
class InvalidVersion(ProblemInModule): pass

class VCSError(Exception):
    def __init__(self, msg, directory):
        self.msg = msg
        self.directory = directory

    def __str__(self):
        return self.msg + ' ({})'.format(self.directory)


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
    # read as bytes to enable custom encodings
    with target.file.open('rb') as f:
        node = ast.parse(f.read())
    for child in node.body:
        # Only use the version from the given module if it's a simple
        # string assignment to __version__
        is_version_str = (isinstance(child, ast.Assign) and
                          len(child.targets) == 1 and
                          child.targets[0].id == "__version__" and
                          isinstance(child.value, ast.Str))
        if is_version_str:
            version = child.value.s
            break
    else:
        version = None
    return ast.get_docstring(node), version

def get_docstring_and_version_via_import(target):
    """
    Return a tuple like (docstring, version) for the given module,
    extracted by importing the module and pulling __doc__ & __version__
    from it.
    """
    log.debug("Loading module %s", target.file)
    sl = SourceFileLoader(target.name, str(target.file))
    with _module_load_ctx():
        m = sl.load_module()
    docstring = m.__dict__.get('__doc__', None)
    version = m.__dict__.get('__version__', None)
    return docstring, version

def get_info_from_module(target: Module):
    """Load the module/package, get its docstring and __version__
    """
    log.debug("Loading module %s", target.file)

    # Attempt to extract our docstring & version by parsing our target's
    # AST, falling back to an import if that fails. This allows us to
    # build without necessarily requiring that our built package's
    # requirements are installed.
    docstring, version = get_docstring_and_version_via_ast(target)
    if not (docstring and version):
        docstring, version = get_docstring_and_version_via_import(target)

    if (not docstring) or not docstring.strip():
        raise NoDocstringError('Flit cannot package module without docstring, '
                'or empty docstring. Please add a docstring to your module '
                '({}).'.format(target.file))

    version = check_version(version)

    docstring_lines = docstring.lstrip().splitlines()
    return {'summary': docstring_lines[0],
            'version': version}

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
                             'Please define a `__version__="x.y.z"` in your module.')
    if not isinstance(version, str):
        raise InvalidVersion('__version__ must be a string, not {}.'
                                .format(type(version)))

    # Import here to avoid circular import
    from .validate import normalise_version
    version = normalise_version(version)

    return version


script_template = """\
#!{interpreter}
from {module} import {func}
if __name__ == '__main__':
    {func}()
"""

def parse_entry_point(ep: str):
    """Check and parse a 'package.module:func' style entry point specification.

    Returns (modulename, funcname)
    """
    if ':' not in ep:
        raise ValueError("Invalid entry point (no ':'): %r" % ep)
    mod, func = ep.split(':')

    if not func.isidentifier():
        raise ValueError("Invalid entry point: %r is not an identifier" % func)
    for piece in mod.split('.'):
        if not piece.isidentifier():
            raise ValueError("Invalid entry point: %r is not a module path" % piece)

    return mod, func

def write_entry_points(d, fp):
    """Write entry_points.txt from a two-level dict

    Sorts on keys to ensure results are reproducible.
    """
    for group_name in sorted(d):
        fp.write('[{}]\n'.format(group_name))
        group = d[group_name]
        for name in sorted(group):
            val = group[name]
            fp.write('{}={}\n'.format(name, val))
        fp.write('\n')

def hash_file(path, algorithm='sha256'):
    with Path(path).open('rb') as f:
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

    home_page = None
    author = None
    maintainer = None
    maintainer_email = None
    license = None
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

    metadata_version = "2.1"

    def __init__(self, data):
        self.name = data.pop('name')
        self.version = data.pop('version')
        self.author_email = data.pop('author_email')
        self.summary = data.pop('summary')

        for k, v in data.items():
            assert hasattr(self, k), "data does not have attribute '{}'".format(k)
            setattr(self, k, v)

    def _normalise_name(self, n):
        return n.lower().replace('-', '_')

    def write_metadata_file(self, fp):
        """Write out metadata in the email headers format"""
        fields = [
            'Metadata-Version',
            'Name',
            'Version',
            'Summary',
            'Home-page',
            'License',
        ]
        optional_fields = [
            'Keywords',
            'Author',
            'Author-email',
            'Maintainer',
            'Maintainer-email',
            'Requires-Python',
            'Description-Content-Type',
        ]

        for field in fields:
            value = getattr(self, self._normalise_name(field))
            fp.write("{}: {}\n".format(field, value or 'UNKNOWN'))

        for field in optional_fields:
            value = getattr(self, self._normalise_name(field))
            if value is not None:
                fp.write("{}: {}\n".format(field, value))

        for clsfr in self.classifiers:
            fp.write('Classifier: {}\n'.format(clsfr))

        for req in self.requires_dist:
            fp.write('Requires-Dist: {}\n'.format(req))

        for url in self.project_urls:
            fp.write('Project-URL: {}\n'.format(url))

        for extra in self.provides_extra:
            fp.write('Provides-Extra: {}\n'.format(extra))

        if self.description is not None:
            fp.write('\n' + self.description + '\n')

    @property
    def supports_py2(self) -> bool:
        """Return True if Requires-Python indicates Python 2 support."""
        for part in (self.requires_python or "").split(","):
            if re.search(r"^\s*(>\s*(=\s*)?)?[3-9]", part):
                return False
        return True


def make_metadata(module, ini_info):
    md_dict = {'name': module.name, 'provides': [module.name]}
    md_dict.update(get_info_from_module(module))
    md_dict.update(ini_info['metadata'])
    return Metadata(md_dict)

def metadata_and_module_from_ini_path(ini_path):
    from . import inifile
    ini_info = inifile.read_pkg_ini(ini_path)
    module = Module(ini_info['module'], ini_path.parent)
    metadata = make_metadata(module, ini_info)
    return metadata,module

def dist_info_name(distribution, version):
    """Get the correct name of the .dist-info folder"""
    escaped_name = re.sub(r"[^\w\d.]+", "_", distribution, flags=re.UNICODE)
    escaped_version = re.sub(r"[^\w\d.]+", "_", version, flags=re.UNICODE)
    return '{}-{}.dist-info'.format(escaped_name, escaped_version)
