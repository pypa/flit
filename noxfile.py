"""Automation using nox.
"""

from pathlib import Path
from typing import Iterator, Tuple

import nox

nox.options.reuse_existing_virtualenvs = True

@nox.session
def vendoring(session: nox.Session) -> None:
    session.install("vendoring~=1.2.0")

    if "--upgrade" not in session.posargs:
        session.run("vendoring", "sync", "-v")
        return

    def pinned_requirements(path: Path) -> Iterator[Tuple[str, str]]:
        for line in path.read_text().splitlines(keepends=False):
            one, sep, two = line.partition("==")
            if not sep:
                continue
            name = one.strip()
            version = two.split("#", 1)[0].strip()
            if name and version:
                yield name, version

    vendor_txt = Path("flit_core/flit_core/_vendor/vendor.txt")
    for name, old_version in pinned_requirements(vendor_txt):

        # update requirements.txt
        session.run("vendoring", "update", ".", name)

        # get the updated version
        new_version = old_version
        for inner_name, inner_version in pinned_requirements(vendor_txt):
            if inner_name == name:
                # this is a dedicated assignment, to make flake8 happy
                new_version = inner_version
                break
        else:
            session.error(f"Could not find {name} in {vendor_txt}")

        # check if the version changed.
        if new_version == old_version:
            continue  # no change, nothing more to do here.

        # synchronize the contents
        session.run("vendoring", "sync", ".")
