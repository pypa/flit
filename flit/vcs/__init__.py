from pathlib import Path
from . import git

def identify_vcs(directory: Path):
    while True:
        if (directory / '.git').is_dir():
            return git

        if directory.parent == directory:
            # Root directory
            raise EnvironmentError("Directory does not appear to be in a VCS")

        directory = directory.parent
