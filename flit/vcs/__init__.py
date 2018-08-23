from pathlib import Path

from setuptools_scm import get_version

from flit.errors import VCSError
from . import hg
from . import git

def identify_vcs(directory: Path):
    directory = directory.resolve()
    for p in [directory] + list(directory.parents):
        if (p / '.git').is_dir():
            return git
        if (p / '.hg').is_dir():
            return hg

    raise VCSError("Directory does not appear to be in a VCS", directory)

def get_version_from_scm(scm_dir: Path) -> str:
    try:
        return get_version(scm_dir)
    except LookupError as exc:
        raise VCSError(
            'Failed to get version from source control: {}'.
            format(str(exc))
        )
