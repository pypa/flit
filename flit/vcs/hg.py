import os
from subprocess import check_output

name = 'hg'

def find_repo_root(directory):
    for p in [directory] + list(directory.parents):
        if (p / '.hg').is_dir():
            return p

def _repo_paths_to_directory_paths(paths, directory):
    # 'hg status' gives paths from repo root, which may not be our directory.
    directory = directory.resolve()
    repo = find_repo_root(directory)
    if directory != repo:
        directory_in_repo = str(directory.relative_to(repo)) + os.sep
        ix = len(directory_in_repo)
        paths = [p[ix:] for p in paths
                 if os.path.normpath(p).startswith(directory_in_repo)]
    return paths


def list_tracked_files(directory):
    outb = check_output(['hg', 'status', '--clean', '--added', '--modified', '--no-status'],
                        cwd=str(directory))
    paths = [os.fsdecode(l) for l in outb.strip().splitlines()]
    return _repo_paths_to_directory_paths(paths, directory)


def list_untracked_deleted_files(directory):
    outb = check_output(['hg', 'status', '--unknown', '--deleted', '--no-status'],
                        cwd=str(directory))
    paths = [os.fsdecode(l) for l in outb.strip().splitlines()]
    return _repo_paths_to_directory_paths(paths, directory)
