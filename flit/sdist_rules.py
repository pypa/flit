"""Generate sdist include/exclude rules for Flit

To use: cd into a folder with pyproject.toml set up for Flit, inside a git
repository. Produce any files that should be excluded (e.g. build docs).
Run 'python -m flit.sdist_rules'. It aims to include all files that are tracked
in git, with as few patterns as feasible.

The output is TOML formatted to be used in pyproject.toml - feel free to add or
remove includes & excludes manually.
"""

import argparse
import glob
import sys
from pathlib import Path

import tomli_w

from flit_core.common import Module
from flit_core.config import read_flit_config
from .vcs.git import list_tracked_files

def read_gitignore(path: Path):
    rules = []
    for line in path.read_text('utf-8').splitlines(keepends=False):
        if (not line.strip()) or line.startswith('#'):
            continue  # Blank line or comment

    exclude = True
    if line.startswith('!'):
        exclude = False
        line = line[1:]

    # TODO: backslash escaping?
    rules.append((exclude, glob.translate(line)))


def is_ignored(path: Path, rules):
    # A later ! rule can re-include an excluded file, so we need to evaluate
    # all the rules
    ignored = False
    for exclude, pattern in rules:
        if pattern.match(path):
            ignored = exclude

    return ignored


def auto_exclude(p: Path):
    """Check if a path will be excluded regardless of config"""
    return p.name == '__pycache__' or p.suffix == '.pyc'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    def debug(*a):
        if args.debug:
            print(*a, file=sys.stderr)

    pyproj_file = Path("pyproject.toml")
    config = read_flit_config(pyproj_file)
    module = Module(config.module)

    auto_inc_files = [pyproj_file] + [Path(s) for s in config.referenced_files]
    auto_inc_dirs = []
    if module.is_package:
        auto_inc_dirs.append(module.path)
    else:
        auto_inc_files.append(module.path)
    if config.data_directory is not None:
        auto_inc_dirs.append(config.data_directory)

    def auto_include(p: Path):
        return p in auto_inc_files or any(p.is_relative_to(d) for d in auto_inc_dirs)

    includes = [p for s in list_tracked_files(".") if not auto_include(p := Path(s))]
    debug(f"{len(includes)} additional files to include in sdist")

    # For each directory containing included files, does including the directory
    # and excluding ignored files mean fewer rules overall
    candidate_dirs = set()
    for path in includes:
        candidate_dirs.update(path.parents[:-1])  # slice off Path(".")

    new_includes = set(includes)
    new_excludes = set()

    for dir in sorted(candidate_dirs, key=lambda p: (-len(p.parts), p)):
        debug(f"Evaluating {dir}")
        included_matches = [p for p in new_includes if p.is_relative_to(dir)]
        add_excludes = [p for p in dir.iterdir()
                        if p not in included_matches and not auto_exclude(p)]

        debug(f"Could replace {len(included_matches)} includes: "
              f"{[str(p.relative_to(dir)) for p in included_matches]}")
        debug(f"Would require {len(add_excludes)} additional excludes: "
              f"{[str(p.relative_to(dir)) for p in add_excludes]}")
        if len(included_matches) > len(add_excludes):
            debug("Replacing")
            new_includes -= set(included_matches)
            new_includes.add(dir)
            new_excludes |= set(add_excludes)
        debug()

    def fmt_path(p: Path) -> str:
        return p.as_posix() + ('/' if p.is_dir() else '')

    print("# The TOML table below can be copied into your pyproject.toml\n")
    print("[tool.flit.sdist]")
    print(tomli_w.dumps({
        "include": sorted([fmt_path(p) for p in new_includes], key=str.lower),
        "exclude": sorted([fmt_path(p) for p in new_excludes], key=str.lower),
    }))


if __name__ == "__main__":
    sys.exit(main())
