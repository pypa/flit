import os
from subprocess import check_output

def list_tracked_files(directory):
    outb = check_output(['git', 'ls-files'], cwd=str(directory))
    return [os.fsdecode(l) for l in outb.strip().splitlines()]
