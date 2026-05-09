from pathlib import Path

from . import hg
from . import git
from . import fsl

def identify_vcs(directory: Path):
    directory = directory.resolve()
    for p in [directory] + list(directory.parents):
        # In a linked git worktree (`git worktree add ...`) or inside a
        # git submodule, `.git` is a regular file containing a
        # `gitdir: <path>` pointer rather than a directory.
        git_entry = p / '.git'
        if git_entry.is_dir() or git_entry.is_file():
            return git
        if (p / '.hg').is_dir():
            return hg
        if ((p / '.fslckout').is_file()
            or (p / '_FOSSIL_').is_file()):
            return fsl

    return None
