import shlex
from functools import wraps
from pathlib import Path
from shutil import copy, copytree, which
from subprocess import check_output

import pytest

samples_dir = Path(__file__).parent / "samples"

skip_if_no_git = pytest.mark.skipif(
    (not which("git")),
    reason="needs git to be installed and findable through the PATH environment variable in order to run these tests",
)


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("needsgit"):
            item.add_marker(skip_if_no_git)


@pytest.fixture
def copy_sample(tmp_path):
    """Copy a subdirectory from the samples dir to a temp dir"""

    def copy(dirname):
        dst = tmp_path / dirname
        copytree(str(samples_dir / dirname), str(dst))
        return dst

    return copy


def git_cmd(repository_path, command):
    if isinstance(command, str):
        args = shlex.split(command)
    else:
        args = command

    return check_output(
        ["git", "-C", str(repository_path), *args],
    )


@pytest.fixture
def tmp_git_repo(tmp_path, monkeypatch):
    """
    Make a git repository in a temporary folder

    The path returned is what should be passed to git's -C command, or what cwd
    should be set to in subprocess calls
    """
    git_global_config = tmp_path / "git_global_config"
    git_global_config.touch(exist_ok=False)
    repository = tmp_path / "repository"
    repository.mkdir(exist_ok=False)

    git_environment_variables = {
        # https://git-scm.com/docs/git#Documentation/git.txt-codeGITCONFIGGLOBALcode
        "GIT_CONFIG_GLOBAL": str(git_global_config),
        # https://git-scm.com/docs/git#Documentation/git.txt-codeGITCONFIGNOSYSTEMcode
        "GIT_CONFIG_NOSYSTEM": "true",
        "HOME": str(tmp_path),
        # https://github.com/git/git/blob/cefe983a320c03d7843ac78e73bd513a27806845/t/test-lib.sh#L454-L461
        "GIT_AUTHOR_EMAIL": "author@example.com",
        "GIT_AUTHOR_NAME": "A U Thor",
        "GIT_AUTHOR_DATE": "1112354055 +0200",
        "GIT_COMMITTER_EMAIL": "committer@example.com",
        "GIT_COMMITTER_NAME": "committer",
        "GIT_COMMITTER_DATE": "1112354055 +0200",
    }
    for name, value in git_environment_variables.items():
        monkeypatch.setenv(name, value)

    # https://github.com/git/git/blob/cefe983a320c03d7843ac78e73bd513a27806845/t/test-lib.sh#L454-L461
    for name in ["XDG_CONFIG_HOME", "XDG_CACHE_HOME"]:
        monkeypatch.delenv(name, raising=False)

    git_cmd(repository, "config --global init.defaultBranch main")
    git_cmd(repository, ["init"])
    git_cmd(repository, "commit --allow-empty --allow-empty-message --no-edit")

    yield repository


@pytest.fixture
def git(tmp_git_repo):
    @wraps(git_cmd)
    def wrapper(command):
        return git_cmd(repository_path=tmp_git_repo, command=command)

    return wrapper


@pytest.fixture
def tmp_project(tmp_git_repo, git):
    "return a path to the root of a git repository containing a sample package"
    for file in (samples_dir / "module1_toml").glob("*"):
        copy(str(file), str(tmp_git_repo / file.name))
    git("add -A :/")
    git("commit --allow-empty --allow-empty-message --no-edit")

    yield tmp_git_repo
