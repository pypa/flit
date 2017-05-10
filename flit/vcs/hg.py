import os
from subprocess import check_output

def find_repo_root(directory):
    for p in [directory] + list(directory.parents):
        if (p / '.hg').is_dir():
            return p

def list_tracked_files(directory):
    outb = check_output(['hg', 'status', '--clean', '--added', '--no-status'],
                        cwd=str(directory))
    paths = [os.fsdecode(l) for l in outb.strip().splitlines()]
    # 'hg status' gives paths from repo root, which may not be our directory.
    repo = find_repo_root(directory)
    if directory != repo:
        directory_in_repo = str(directory.relative_to(repo))
        paths = [p for p in paths
                 if os.path.normpath(p).startswith(directory_in_repo)]
    return paths
