"""get_dirs() is pulled out as a separate file so we can run it in a target Python.
"""
import os
import sys
import sysconfig

def get_dirs(user=True):
    """Get the 'scripts' and 'purelib' directories we'll install into.

    This is now a thin wrapper around sysconfig.get_paths(). It's not inlined,
    because some tests mock it out to install to a different location.
    """
    if user:
        if (sys.platform == "darwin") and sysconfig.get_config_var('PYTHONFRAMEWORK'):
            return sysconfig.get_paths('osx_framework_user')
        return sysconfig.get_paths(os.name + '_user')
    else:
        # The default scheme is 'posix_prefix' or 'nt', and should work for e.g.
        # installing into a virtualenv
        return sysconfig.get_paths()


if __name__ == '__main__':
    import json
    user = '--user'in sys.argv
    dirs = get_dirs(user)
    json.dump(dirs, sys.stdout)
