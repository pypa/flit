import builtins
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from testpath import assert_isfile
from unittest.mock import patch
import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from flit import init


@contextmanager
def patch_data_dir():
    with TemporaryDirectory() as td:
        with patch.object(init, 'get_data_dir', lambda: Path(td)):
            yield td

def test_store_defaults():
    with patch_data_dir():
        assert init.get_defaults() == {}
        d = {'author': 'Test'}
        init.store_defaults(d)
        assert init.get_defaults() == d

def fake_input(entries):
    it = iter(entries)
    def inner(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return inner

def faking_input(entries):
    return patch.object(builtins, 'input', fake_input(entries))

def test_prompt_options():
    ti = init.TerminalIniter()
    with faking_input(['4', '1']):
        res = ti.prompt_options('Pick one', [('A', 'Apple'), ('B', 'Banana')])
    assert res == 'A'

    # Test with a default
    with faking_input(['']):
        res = ti.prompt_options('Pick one', [('A', 'Apple'), ('B', 'Banana')],
                                default='B')
    assert res == 'B'

@contextmanager
def make_dir(files=(), dirs=()):
    with TemporaryDirectory() as td:
        tdp = Path(td)
        for d in dirs:
            (tdp / d).mkdir()
        for f in files:
            (tdp / f).touch()
        yield td

def test_guess_module_name():
    with make_dir(['foo.py', 'foo-bar.py', 'test_foo.py', 'setup.py']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() == 'foo'

    with make_dir(['baz/__init__.py', 'tests/__init__.py'], ['baz', 'tests']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() == 'baz'

    with make_dir(['src/foo.py', 'src/foo-bar.py', 'test_foo.py', 'setup.py'],
                  ['src',]) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() == 'foo'

    with make_dir(['src/baz/__init__.py', 'tests/__init__.py'], ['src', 'src/baz', 'tests']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() == 'baz'

    with make_dir(['foo.py', 'bar.py']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() is None

    with make_dir(['src/foo.py', 'src/bar.py'], ['src']) as td:
        ib = init.IniterBase(td)
        assert ib.guess_module_name() is None

def test_write_license():
    with TemporaryDirectory() as td:
        ib = init.IniterBase(td)
        ib.write_license('mit', 'Thomas Kluyver')
        assert_isfile(Path(td, 'LICENSE'))

def test_init():
    responses = ['foo', # Module name
                 'Test Author',      # Author
                 'test@example.com',  # Author email
                 'http://example.com/', # Home page
                 '1'    # License (1 -> MIT)
                ]
    with TemporaryDirectory() as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()

        generated = Path(td) / 'pyproject.toml'
        assert_isfile(generated)
        with generated.open('rb') as f:
            data = tomllib.load(f)
        assert data['project']['authors'][0]['email'] == "test@example.com"
        license = Path(td) / 'LICENSE'
        assert data['project']['license'] == 'MIT'
        assert data['project']['license-files'] == ['LICENSE']
        assert_isfile(license)
        with license.open() as f:
            license_text = f.read()
        assert license_text.startswith("Copyright (c)")
        assert "Permission is hereby granted, free of charge" in license_text
        assert "{year}" not in license_text
        assert "Test Author" in license_text

def test_init_homepage_and_license_are_optional():
    responses = ['test_module_name',
                 'Test Author',
                 'test_email@example.com',
                 '',   # Home page omitted
                 '4',  # Skip - choose a license later
                ]
    with TemporaryDirectory() as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()
        with Path(td, 'pyproject.toml').open('rb') as f:
            data = tomllib.load(f)
        assert not Path(td, 'LICENSE').exists()
    assert data['project'] == {
        'authors': [{'name': 'Test Author', 'email': 'test_email@example.com'}],
        'name': 'test_module_name',
        'dynamic': ['version', 'description'],
    }

def test_init_homepage_validator():
    responses = ['test_module_name',
                 'Test Author',
                 'test_email@example.com',
                 'www.uh-oh-spagghetti-o.com',  # fails validation
                 'https://www.example.org',  # passes
                 '4',  # Skip - choose a license later
                ]
    with TemporaryDirectory() as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()
        with Path(td, 'pyproject.toml').open('rb') as f:
            data = tomllib.load(f)
    assert data['project'] == {
        'authors': [{'name': 'Test Author', 'email': 'test_email@example.com'}],
        'name': 'test_module_name',
        'urls': {'Home': 'https://www.example.org'},
        'dynamic': ['version', 'description'],
    }

def test_author_email_field_is_optional():
    responses = ['test_module_name',
                 'Test Author',
                 '',  # Author-email field is skipped
                 'https://www.example.org',
                 '4',
                ]
    with TemporaryDirectory() as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()
        with Path(td, 'pyproject.toml').open('rb') as f:
            data = tomllib.load(f)
        assert not Path(td, 'LICENSE').exists()

    assert data['project'] == {
        'authors': [{'name': 'Test Author'}],
        'name': 'test_module_name',
        'urls': {'Home': 'https://www.example.org'},
        'dynamic': ['version', 'description'],
    }


@pytest.mark.parametrize(
    "readme_file",
    ["readme.md", "README.MD", "README.md",
     "Readme.md", "readme.MD", "readme.rst",
     "readme.txt"])
def test_find_readme(readme_file):
    with make_dir([readme_file]) as td:
        ib = init.IniterBase(td)
        assert ib.find_readme() == readme_file


def test_find_readme_not_found():
    with make_dir() as td:
        ib = init.IniterBase(td)
        assert ib.find_readme() is None


def test_init_readme_found_yes_choosen():
    responses = ['test_module_name',
                 'Test Author',
                 'test_email@example.com',
                 '',   # Home page omitted
                 '4',  # Skip - choose a license later
                ]
    with make_dir(["readme.md"]) as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()
        with Path(td, 'pyproject.toml').open('rb') as f:
            data = tomllib.load(f)

    assert data['project'] == {
        'authors': [{'name': 'Test Author', 'email': 'test_email@example.com'}],
        'name': 'test_module_name',
        'readme': 'readme.md',
        'dynamic': ['version', 'description'],
    }


def test_init_non_ascii_author_name():
    responses = ['foo', # Module name
                 'Test Authôr',      # Author
                 '',  # Author email omitted
                 '', # Home page omitted
                 '1'    # License (1 -> MIT)
                ]
    with TemporaryDirectory() as td, \
          patch_data_dir(), \
          faking_input(responses):
        ti = init.TerminalIniter(td)
        ti.initialise()

        generated = Path(td) / 'pyproject.toml'
        assert_isfile(generated)
        with generated.open('r', encoding='utf-8') as f:
            raw_text = f.read()
            print(raw_text)
            assert "Test Authôr" in raw_text
            assert "\\u00f4" not in raw_text
        license = Path(td) / 'LICENSE'
        assert_isfile(license)
        with license.open(encoding='utf-8') as f:
            license_text = f.read()
        assert "Test Authôr" in license_text
