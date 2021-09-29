from pathlib import Path
from shutil import copy, copytree, which
from subprocess import check_output
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from typing import Iterator, List, Union

samples_dir = Path(__file__).parent / "samples"

skip_if_no_git = pytest.mark.skipif(
    (not which("git")),
    reason="needs git to be installed and findable through the PATH environment variable",
)


def pytest_collection_modifyitems(items):
    for item in items:
        if "needgit" in item.nodeid or "needsgit" in item.nodeid:
            item.add_marker(skip_if_no_git)
            item.add_marker(pytest.mark.needgit)
            item.add_marker(pytest.mark.needsgit)


@pytest.fixture
def copy_sample(tmp_path):
    """Copy a subdirectory from the samples dir to a temp dir"""

    def copy(dirname):
        dst = tmp_path / dirname
        copytree(str(samples_dir / dirname), str(dst))
        return dst

    return copy


def git(repo: Path, command: "Union[List[str], str]") -> bytes:
    if isinstance(command, str):
        args = command.split()
    else:
        args = command

    return check_output(
        ["git", "-C", str(repo), *args],
    )


@pytest.fixture
def tmp_git(tmp_path: Path) -> "Iterator[Path]":
    """
    Make a git repository in a temporary folder

    The path returned is what should be passed to git's -C command, or what cwd
    should be set to in subprocess calls
    """
    git_global_config = tmp_path / "git_global_config"
    git_global_config.touch(exist_ok=False)
    repository = tmp_path / "repository"
    repository.mkdir(exist_ok=False)
    with patch.dict(
        "os.environ",
        {
            # https://git-scm.com/docs/git#Documentation/git.txt-codeGITCONFIGGLOBALcode
            "GIT_CONFIG_GLOBAL": str(git_global_config),
            # https://git-scm.com/docs/git#Documentation/git.txt-codeGITCONFIGNOSYSTEMcode
            "GIT_CONFIG_NOSYSTEM": "true",
            "HOME": str(tmp_path),
            # tox by default only passes the PATH environment variable, so
            # XDG_CONFIG_HOME is already unset
            # https://github.com/git/git/blob/cefe983a320c03d7843ac78e73bd513a27806845/t/test-lib.sh#L454-L461
            "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_AUTHOR_NAME": "A U Thor",
            "GIT_AUTHOR_DATE": "1112354055 +0200",
            "GIT_COMMITTER_EMAIL": "committer@example.com",
            "GIT_COMMITTER_NAME": "committer",
            "GIT_COMMITTER_DATE": "1112354055 +0200",
        },
    ):
        git(repository, "config --global init.defaultBranch main")
        git(repository, ["init"])
        git(repository, "commit --allow-empty --allow-empty-message --no-edit")

        yield repository


@pytest.fixture
def tmp_project(tmp_git: Path) -> "Iterator[Path]":
    "return a path to the root of a git repository containing a sample package"
    for file in (samples_dir / "module1_toml").glob("*"):
        copy(str(file), str(tmp_git / file.name))
    git(tmp_git, "add -A :/")
    git(tmp_git, "commit --allow-empty --allow-empty-message --no-edit")

    yield tmp_git
