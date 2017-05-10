from pathlib import Path
from . import hg
from . import git

def identify_vcs(directory: Path):
    for p in [directory] + list(directory.parents):
        if (p / '.git').is_dir():
            return git
        if (p / '.hg').is_dir():
            return hg

    raise EnvironmentError("Directory does not appear to be in a VCS")
