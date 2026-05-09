import os
import os.path as osp
from subprocess import check_output

name = 'git'

def list_tracked_files(directory):
    outb = check_output(['git', 'ls-files', '--recurse-submodules', '-z'],
                        cwd=str(directory))
    # NOTE: os.fsdecode() may cause issues if git returns path names that
    # aren't in the filesystem encoding
    return [osp.normpath(os.fsdecode(l)) for l in outb.strip(b'\0').split(b'\0') if l]

def list_untracked_deleted_files(directory):
    outb = check_output(['git', 'ls-files', '--deleted', '--others',
                         '--exclude-standard', '-z'],
                        cwd=str(directory))
    return [osp.normpath(os.fsdecode(l)) for l in outb.strip(b'\0').split(b'\0') if l]
