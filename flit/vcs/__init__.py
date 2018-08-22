from pathlib import Path

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
