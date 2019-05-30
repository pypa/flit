import os
import enscons
import pytoml as toml

from subprocess import check_output

from flit import __version__

metadata = dict(toml.load(open("pyproject.toml")))["tool"]["flit"]["metadata"]
metadata.update({
    "name": "flit",
    "version": __version__,
    "description_file": "README.rst",
    "entry_points": {
        "flit": "flit:main"
    }
})

# set to True if package is not pure Python
HAS_NATIVE_CODE = False

full_tag = "py3-nae-any"

env = Environment(
    tools=["default", "packaging", enscons.generate],
    PACKAGE_METADATA=metadata,
    WHEEL_TAG=full_tag,
    ROOT_IS_PURELIB=full_tag.endswith("-any"),
)

outb = check_output(['git', 'ls-files'], cwd=str('.'))
tracked_files = [os.fsdecode(l) for l in outb.strip().splitlines()]

# Only *.py is included automatically by setup2toml.
# Add extra 'purelib' files or package_data here.
py_source = [f for f in tracked_files if f.startswith('flit/')]

lib = env.Whl("platlib" if HAS_NATIVE_CODE else "purelib", py_source, root='.')

lic = env.Command(env["DIST_INFO_PATH"].File("LICENSE"), "LICENSE", [Copy("$TARGET", "$SOURCE")])

whl = env.WhlFile([lib, lic])

# Add automatic source files, plus any other needed files.
sdist_source = tracked_files + ["PKG-INFO"]

sdist = env.SDist(source=sdist_source)

env.NoClean(sdist)
env.Alias("sdist", sdist)

# needed for pep517 / enscons.api to work
env.Default(whl, sdist)
