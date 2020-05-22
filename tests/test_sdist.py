import ast
from os.path import join as pjoin
from pathlib import Path
import pytest
from shutil import which, copy, copytree
import sys
import tarfile
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
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1' / 'pyproject.toml')
    with TemporaryDirectory() as td:
        td = Path(td)
        builder.build(td)
        sdist_file = td / 'package1-0.1.tar.gz'
        assert_isfile(sdist_file)

        with tarfile.open(str(sdist_file)) as tf:
            assert 'package1-0.1/setup.py' in tf.getnames()


def test_sdist_no_setup_py():
    # Smoke test of making a complete sdist
    if not which('git'):
        pytest.skip("requires git")
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1' / 'pyproject.toml')
    with TemporaryDirectory() as td:
        td = Path(td)
        builder.build(td, gen_setup_py=False)
        sdist_file = td / 'package1-0.1.tar.gz'
        assert_isfile(sdist_file)

        with tarfile.open(str(sdist_file)) as tf:
            assert 'package1-0.1/setup.py' not in tf.getnames()


LIST_FILES = """\
#!{python}
import sys
from os.path import join
if '--deleted' not in sys.argv:
    files = [
        'foo',
        join('dir1', 'bar'),
        join('dir1', 'subdir', 'qux'),
        join('dir2', 'abc'),
        join('dist', 'def'),
    ]
    mode = '{vcs}'
    if mode == 'git':
        print('\\0'.join(files), end='\\0')
    elif mode == 'hg':
        for f in files:
            print(f)
"""

LIST_FILES_GIT = LIST_FILES.format(python=sys.executable, vcs='git')
LIST_FILES_HG = LIST_FILES.format(python=sys.executable, vcs='hg')


def test_get_files_list_git(copy_sample):
    td = copy_sample('module1_toml')
    (td / '.git').mkdir()

    builder = sdist.SdistBuilder.from_ini_path(td / 'pyproject.toml')
    with MockCommand('git', LIST_FILES_GIT):
        files = builder.select_files()

    assert set(files) == {
        'foo', pjoin('dir1', 'bar'), pjoin('dir1', 'subdir', 'qux'),
        pjoin('dir2', 'abc')
    }

def test_get_files_list_hg(tmp_path):
    dir1 = tmp_path / 'dir1'
    copytree(str(samples_dir / 'module1_toml'), str(dir1))
    (tmp_path / '.hg').mkdir()
    builder = sdist.SdistBuilder.from_ini_path(dir1 / 'pyproject.toml')
    with MockCommand('hg', LIST_FILES_HG):
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
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1' / 'pyproject.toml')
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

def test_make_setup_py_package_dir_src():
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'packageinsrc' / 'pyproject.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['package_dir'] == {'': 'src'}
