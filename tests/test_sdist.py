import ast
from io import BytesIO
from os.path import join as pjoin
from pathlib import Path
import pytest
from shutil import which, copy
import sys
import tarfile
from tempfile import TemporaryDirectory
from testpath import assert_isfile, MockCommand

from flit import sdist
import flit_core.sdist as sdist_core

samples_dir = Path(__file__).parent / 'samples'

def test_auto_packages():
    packages, pkg_data = sdist.auto_packages(str(samples_dir / 'package1'))
    assert packages == ['package1', 'package1.subpkg', 'package1.subpkg2']
    assert pkg_data == {'': ['*'],
                        'package1': ['data_dir/*'],
                        'package1.subpkg': ['sp_data_dir/*'],
                       }

def test_make_sdist():
    # Smoke test of making a complete sdist
    if not which('git'):
        pytest.skip("requires git")
    builder = sdist.SdistBuilder(samples_dir / 'package1-pkg.ini')
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


def test_get_files_list_git():
    with TemporaryDirectory() as td:
        copy(str(samples_dir / 'module1.py'), td)
        copy(str(samples_dir / 'module1-pkg.ini'), td)
        td = Path(td)
        (td / '.git').mkdir()
        builder = sdist.SdistBuilder(td / 'module1-pkg.ini')
        with MockCommand('git', LIST_FILES):
            files = builder.select_files()

        assert set(files) == {
            'foo', pjoin('dir1', 'bar'), pjoin('dir1', 'subdir', 'qux'),
            pjoin('dir2', 'abc')
        }

def test_get_files_list_hg():
    with TemporaryDirectory() as td:
        dir1 = Path(td, 'dir1')
        dir1.mkdir()
        copy(str(samples_dir / 'module1.py'), str(dir1))
        copy(str(samples_dir / 'module1-pkg.ini'), str(dir1))
        td = Path(td)
        (td / '.hg').mkdir()
        builder = sdist.SdistBuilder(dir1 / 'module1-pkg.ini')
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
    builder = sdist.SdistBuilder(samples_dir / 'package1-pkg.ini')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['packages'] == ['package1', 'package1.subpkg', 'package1.subpkg2']
    assert 'install_requires' not in ns
    assert ns['entry_points'] == \
           {'console_scripts': ['pkg_script = package1:main']}

def test_make_setup_py_reqs():
    builder = sdist.SdistBuilder(samples_dir / 'extras.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['install_requires'] == ['toml']
    assert ns['extras_require'] == {'test': ['pytest'], 'custom': ['requests']}

def test_make_setup_py_reqs_envmark():
    builder = sdist.SdistBuilder(samples_dir / 'requires-envmark.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['install_requires'] == ['requests']
    assert ns['extras_require'] == {":python_version == '2.7'": ['pathlib2']}

def test_make_setup_py_reqs_extra_envmark():
    builder = sdist.SdistBuilder(samples_dir / 'requires-extra-envmark.toml')
    ns = get_setup_assigns(builder.make_setup_py())
    assert ns['extras_require'] == {'test:python_version == "2.7"': ['pathlib2']}

def test_clean_tarinfo():
    with tarfile.open(mode='w', fileobj=BytesIO()) as tf:
        ti = tf.gettarinfo(str(samples_dir / 'module1.py'))
    cleaned = sdist_core.clean_tarinfo(ti, mtime=42)
    assert cleaned.uid == 0
    assert cleaned.uname == ''
    assert cleaned.mtime == 42
