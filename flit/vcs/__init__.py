import subprocess
from pathlib import Path

from . import hg
from . import git

def git_validate_ignore(directory: Path) -> bool:
    check_ignore = subprocess.run(
        ['git', 'check-ignore', '.'],
        cwd=str(directory),
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    ).returncode
    if check_ignore == 0:
        return False
    return True

def identify_vcs(directory: Path):
    directory = directory.resolve()
    for p in [directory] + list(directory.parents):
        if (p / '.git').is_dir() and git_validate_ignore(directory):
            return git
        if (p / '.hg').is_dir():
            return hg

    return None
