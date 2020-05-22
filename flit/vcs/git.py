import os
from subprocess import check_output

name = 'git'

def list_tracked_files(directory):
    outb = check_output(['git', 'ls-files', '--recurse-submodules', '-z'],
                        cwd=str(directory))
    return [os.fsdecode(l) for l in outb.strip(b'\0').split(b'\0') if l]

def list_untracked_deleted_files(directory):
    outb = check_output(['git', 'ls-files', '--deleted', '--others',
                         '--exclude-standard', '-z'],
                        cwd=str(directory))
    return [os.fsdecode(l) for l in outb.strip(b'\0').split(b'\0') if l]
