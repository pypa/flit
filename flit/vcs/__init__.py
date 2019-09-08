from pathlib import Path

from . import hg
from . import git

def identify_vcs(directory: Path):
    directory = directory.resolve()
    for p in [directory] + list(directory.parents):
        if (p / '.git').is_dir():
            return git
        if (p / '.hg').is_dir():
            return hg

    return None
