import errno
import pytest
import responses

from flit import validate as fv

def test_validate_entrypoints():
    assert fv.validate_entrypoints(
        {'console_scripts': {'flit': 'flit:main'}}) == []
    assert fv.validate_entrypoints(
        {'some.group': {'flit': 'flit.buildapi'}}) == []

    res = fv.validate_entrypoints({'some.group': {'flit': 'a:b:c'}})
    assert len(res) == 1

def test_validate_name():
    def check(name):
        return fv.validate_name({'name': name})

    assert check('foo.bar_baz') == []
    assert check('5minus6') == []

    assert len(check('_foo')) == 1  # Must start with alphanumeric
    assert len(check('foo.')) == 1  # Must end with alphanumeric
    assert len(check('Bücher')) == 1 # ASCII only

def test_validate_requires_python():
    assert fv.validate_requires_python({}) == []  # Not required

    def check(spec):
        return fv.validate_requires_python({'requires_python': spec})

    assert check('>=3') == []
    assert check('>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*') == []

    assert len(check('3')) == 1
    assert len(check('@12')) == 1
    assert len(check('>=2.7; !=3.0.*')) == 1  # Comma separated, not semicolon

def test_validate_requires_dist():
    assert fv.validate_requires_dist({}) == []  # Not required

    def check(spec):
        return fv.validate_requires_dist({'requires_dist': [spec]})

    assert check('requests') == []
    assert check('requests[extra-foo]') == []
    assert check('requests (>=2.14)') == []  # parentheses allowed but not recommended
    assert check('requests >=2.14') == []
    assert check('pexpect; sys_platform == "win32"') == []
    # Altogether now
    assert check('requests[extra-foo] >=2.14; python_version < "3.0"') == []

    # URL specifier
    assert check('requests @ https://example.com/requests.tar.gz') == []
    assert check(
        'requests @ https://example.com/requests.tar.gz ; python_version < "3.8"'
    ) == []

    # Problems
    assert len(check('Bücher')) == 1
    assert len(check('requests 2.14')) == 1
    assert len(check('pexpect; sys.platform == "win32"')) == 1  # '.' -> '_'
    assert len(check('requests >=2.14 @ https://example.com/requests.tar.gz')) == 1
    # Several problems in one requirement
    assert len(check('pexpect[_foo] =3; sys.platform == "win32"')) == 3

def test_validate_environment_marker():
    vem = fv.validate_environment_marker

    assert vem('python_version >= "3" and os_name == \'posix\'') == []

    res = vem('python_version >= "3')  # Unclosed string
    assert len(res) == 1
    assert res[0].startswith("Invalid string")

    res = vem('python_verson >= "3"')  # Misspelled name
    assert len(res) == 1
    assert res[0].startswith("Invalid variable")

    res = vem("os_name is 'posix'")  # No 'is' comparisons
    assert len(res) == 1
    assert res[0].startswith("Invalid expression")

    res = vem("'2' < python_version < '4'")  # No chained comparisons
    assert len(res) == 1
    assert res[0].startswith("Invalid expression")

    assert len(vem('os.name == "linux\'')) == 2

def test_validate_url():
    vurl = fv.validate_url
    assert vurl('https://github.com/takluyver/flit') == []

    assert len(vurl('github.com/takluyver/flit')) == 1
    assert len(vurl('https://')) == 1

def test_validate_project_urls():
    vpu = fv.validate_project_urls

    def check(prurl):
        return vpu({'project_urls': [prurl]})
    assert vpu({}) == []   # Not required
    assert check('Documentation, https://flit.readthedocs.io/') == []

    # Missing https://
    assert len(check('Documentation, flit.readthedocs.io')) == 1
    # Double comma
    assert len(check('A, B, flit.readthedocs.io')) == 1
    # No name
    assert len(check(', https://flit.readthedocs.io/')) == 1
    # Name longer than 32 chars
    assert len(check('Supercalifragilisticexpialidocious, https://flit.readthedocs.io/')) == 1


def test_read_classifiers_cached(monkeypatch, tmp_path):

    def mock_get_cache_dir():
        tmp_file = tmp_path / "classifiers.lst"
        with tmp_file.open("w") as fh:
            fh.write("A\nB\nC")
        return tmp_path

    monkeypatch.setattr(fv, "get_cache_dir", mock_get_cache_dir)

    classifiers = fv._read_classifiers_cached()

    assert classifiers == {'A', 'B', 'C'}


@responses.activate
def test_download_and_cache_classifiers(monkeypatch, tmp_path):
    responses.add(
        responses.GET,
        'https://pypi.org/pypi?%3Aaction=list_classifiers',
        body="A\nB\nC")

    def mock_get_cache_dir():
        return tmp_path

    monkeypatch.setattr(fv, "get_cache_dir", mock_get_cache_dir)

    classifiers = fv._download_and_cache_classifiers()

    assert classifiers == {"A", "B", "C"}


@responses.activate
@pytest.mark.parametrize("error", [PermissionError, OSError(errno.EROFS, "")])
def test_download_and_cache_classifiers_with_unacessible_dir(monkeypatch, error):
    responses.add(
        responses.GET,
        'https://pypi.org/pypi?%3Aaction=list_classifiers',
        body="A\nB\nC")

    class MockCacheDir:
        def mkdir(self, parents):
            raise error
        def __truediv__(self, other):
            raise error

    monkeypatch.setattr(fv, "get_cache_dir", MockCacheDir)

    classifiers = fv._download_and_cache_classifiers()

    assert classifiers == {"A", "B", "C"}


def test_verify_classifiers_valid_classifiers():
    classifiers = {"A"}
    valid_classifiers = {"A", "B"}

    problems = fv._verify_classifiers(classifiers, valid_classifiers)

    assert problems == []

def test_verify_classifiers_invalid_classifiers():
    classifiers = {"A", "B"}
    valid_classifiers = {"A"}

    problems = fv._verify_classifiers(classifiers, valid_classifiers)

    assert problems == ["Unrecognised classifier: 'B'"]

def test_validate_readme_rst():
    metadata = {
        'description_content_type': 'text/x-rst',
        'description': "Invalid ``rst'",
    }
    problems = fv.validate_readme_rst(metadata)

    assert len(problems) == 2  # 1 message that rst is invalid + 1 with details
    assert "valid rst" in problems[0]

    # Markdown should be ignored
    metadata = {
        'description_content_type': 'text/markdown',
        'description': "Invalid `rst'",
    }
    problems = fv.validate_readme_rst(metadata)

    assert problems == []

RST_WITH_CODE = """
Code snippet:

.. code-block:: python

   a = [i ** 2 for i in range(5)]
"""

def test_validate_readme_rst_code():
    # Syntax highlighting shouldn't require pygments
    metadata = {
        'description_content_type': 'text/x-rst',
        'description': RST_WITH_CODE,
    }
    problems = fv.validate_readme_rst(metadata)
    for p in problems:
        print(p)

    assert problems == []
