import ast
from os.path import join as pjoin
from pathlib import Path
import pytest
from shutil import which, copy, copytree
import sys
from tempfile import TemporaryDirectory
from testpath import assert_isfile, MockCommand

from flit import sdist

samples_dir = Path(__file__).parent / 'samples'

def test_auto_packages():
    packages, pkg_data = sdist.auto_packages(str(samples_dir / 'package1' / 'package1'))
    assert packages == ['package1', 'package1.subpkg', 'package1.subpkg2']
    assert pkg_data == {'': ['*'],
                        'package1': ['data_dir/*'],
                        'package1.subpkg': ['sp_data_dir/*'],
                       }

def test_make_sdist():
    # Smoke test of making a complete sdist
    if not which('git'):
        pytest.skip("requires git")
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1' / 'flit.ini')
    with TemporaryDirectory() as td:
        td = Path(td)
        builder.build(td)
        assert_isfile(td / 'package1-0.1.tar.gz')


LIST_FILES = """\
#!{python}
import sys
from os.path import join
if '--deleted' not in sys.argv:
    print('foo')
    print(join('dir1', 'bar'))
    print(join('dir1', 'subdir', 'qux'))
    print(join('dir2', 'abc'))
    print(join('dist', 'def'))
""".format(python=sys.executable)


def test_get_files_list_git(copy_sample):
    td = copy_sample('module1')
    (td / '.git').mkdir()

    builder = sdist.SdistBuilder.from_ini_path(td / 'flit.ini')
    with MockCommand('git', LIST_FILES):
        files = builder.select_files()

    assert set(files) == {
        'foo', pjoin('dir1', 'bar'), pjoin('dir1', 'subdir', 'qux'),
        pjoin('dir2', 'abc')
    }

def test_get_files_list_hg(tmp_path):
    dir1 = tmp_path / 'dir1'
    copytree(str(samples_dir / 'module1'), str(dir1))
    (tmp_path / '.hg').mkdir()
    builder = sdist.SdistBuilder.from_ini_path(dir1 / 'flit.ini')
    with MockCommand('hg', LIST_FILES):
        files = builder.select_files()

    assert set(files) == {
        'bar', pjoin('subdir', 'qux')
    }

def get_setup_assigns(setup):
    """Parse setup.py, execute assignments, return the namespace"""
    setup_ast = ast.parse(setup)
    # Select only assignment statements
    setup_ast.body = [n for n in setup_ast.body if isinstance(n, ast.Assign)]
    ns = {}
    exec(compile(setup_ast, filename="setup.py", mode="exec"), ns)
    return ns

def test_make_setup_py():
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1' / 'flit.ini')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['packages'] == ['package1', 'package1.subpkg', 'package1.subpkg2']
    assert 'install_requires' not in ns
    assert ns['entry_points'] == \
           {'console_scripts': ['pkg_script = package1:main']}

def test_make_setup_py_reqs():
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'extras' / 'pyproject.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['install_requires'] == ['toml']
    assert ns['extras_require'] == {'test': ['pytest'], 'custom': ['requests']}

def test_make_setup_py_reqs_envmark():
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'requires-envmark' / 'pyproject.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['install_requires'] == ['requests']
    assert ns['extras_require'] == {":python_version == '2.7'": ['pathlib2']}

def test_make_setup_py_reqs_extra_envmark():
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'requires-extra-envmark' / 'pyproject.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['extras_require'] == {'test:python_version == "2.7"': ['pathlib2']}
