import os
from subprocess import check_output

name = 'fossil'

def find_repo_root(directory):
    for p in [directory] + list(directory.parents):
        if ((p / '.fslckout').is_file()
            or (p / '_FOSSIL_').is_file()):
            return p

def _repo_paths_to_directory_paths(paths, directory):
    # 'fossil ls' gives paths from repo root, which may not be our directory.
    repo = find_repo_root(directory)
    if directory != repo:
        directory_in_repo = str(directory.relative_to(repo)) + os.sep
        ix = len(directory_in_repo)
        paths = [p[ix:] for p in paths
                 if os.path.normpath(p).startswith(directory_in_repo)]
    return paths


def list_tracked_files(directory):
    outb = check_output(['fossil', 'ls'], cwd=str(directory))
    paths = [os.fsdecode(l) for l in outb.strip().splitlines()]
    return _repo_paths_to_directory_paths(paths, directory)


def list_untracked_deleted_files(directory):
    outb = check_output(['fossil', 'extra'], cwd=str(directory))
    paths = [os.fsdecode(l) for l in outb.strip().splitlines()]
    return _repo_paths_to_directory_paths(paths, directory)
