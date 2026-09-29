from io import BytesIO
import os.path as osp
from pathlib import Path
import tarfile
from testpath import assert_isfile

from flit_core import sdist

samples_dir = Path(__file__).parent / 'samples'

def test_make_sdist(tmp_path):
    # Smoke test of making a complete sdist
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'package1.toml')
    builder.build(tmp_path)
    assert_isfile(tmp_path / 'package1-0.1.tar.gz')


def test_make_sdist_pep621(tmp_path):
    builder = sdist.SdistBuilder.from_ini_path(samples_dir / 'pep621' / 'pyproject.toml')
    path = builder.build(tmp_path)
    assert path == tmp_path / 'module1-0.1.tar.gz'
    assert_isfile(path)


def test_make_sdist_pep621_nodynamic(tmp_path):
    builder = sdist.SdistBuilder.from_ini_path(
        samples_dir / 'pep621_nodynamic' / 'pyproject.toml'
    )
    path = builder.build(tmp_path)
    assert path == tmp_path / 'module1-0.3.tar.gz'
    assert_isfile(path)


def test_clean_tarinfo():
    with tarfile.open(mode='w', fileobj=BytesIO()) as tf:
        ti = tf.gettarinfo(str(samples_dir / 'module1.py'))
    cleaned = sdist.clean_tarinfo(ti, mtime=42)
    assert cleaned.uid == 0
    assert cleaned.uname == ''
    assert cleaned.mtime == 42


def test_include_exclude():
    builder = sdist.SdistBuilder.from_ini_path(
        samples_dir / 'inclusion' / 'pyproject.toml'
    )
    files = builder.apply_includes_excludes(builder.select_files())

    assert osp.join('doc', 'test.rst') in files
    assert osp.join('doc', 'test.txt') not in files
    assert osp.join('doc', 'subdir', 'test.txt') in files
    assert osp.join('doc', 'subdir', 'subsubdir', 'test.md') not in files


def test_data_dir():
    builder = sdist.SdistBuilder.from_ini_path(
        samples_dir / 'with_data_dir' / 'pyproject.toml'
    )
    files = builder.apply_includes_excludes(builder.select_files())

    assert osp.join('data', 'share', 'man', 'man1', 'foo.1') in files


def test_pep625(tmp_path):
    builder = sdist.SdistBuilder.from_ini_path(
        samples_dir / 'normalization' / 'pyproject.toml'
    )
    path = builder.build(tmp_path)
    assert path == tmp_path / 'my_python_module-0.0.1.tar.gz'
    assert_isfile(path)

def test_license_inside_src(tmp_path):
    builder = sdist.SdistBuilder.from_ini_path(
        samples_dir / 'license_in_src' / 'pyproject.toml'
    )
    path = builder.build(tmp_path)

    with tarfile.open(path, 'r|*') as tar:
        lic_count = sum(
            1 for member in iter(tar.next, None)
            if member.name == 'license_in_src-0/license_in_src/lic.txt'
        )

    assert lic_count == 1


def test_recursive_glob_dotfiles(tmp_path):
    (tmp_path / 'pkg').mkdir()
    (tmp_path / 'pkg' / '__init__.py').write_text('"""A sample package"""\n__version__ = "0.1"\n')
    (tmp_path / 'pkg' / 'sub').mkdir()
    (tmp_path / 'pkg' / 'sub' / '.hidden.swp').write_text('swap')
    (tmp_path / 'pkg' / '.root.swp').write_text('swap')
    (tmp_path / 'pkg' / 'normal.txt').write_text('normal')

    patterns = sdist.FilePatterns(['**/*.swp'], str(tmp_path))
    assert patterns.match_file(osp.join('pkg', '.root.swp'))
    assert patterns.match_file(osp.join('pkg', 'sub', '.hidden.swp'))
    assert not patterns.match_file(osp.join('pkg', 'normal.txt'))


def test_sdist_exclude_dotfiles(tmp_path):
    pkg_dir = tmp_path / 'pkg'
    pkg_dir.mkdir()
    (pkg_dir / '__init__.py').write_text('"""A sample package"""\n__version__ = "0.1"\n')
    (pkg_dir / 'sub').mkdir()
    (pkg_dir / 'sub' / '.editor.swp').write_text('swap')
    (pkg_dir / '.main.swp').write_text('swap')
    (pkg_dir / 'module.py').write_text('x = 1\n')

    pyproject = tmp_path / 'pyproject.toml'
    pyproject.write_text("""
[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"

[project]
name = "pkg"
authors = [{name = "Test"}]
dynamic = ["version", "description"]

[tool.flit.sdist]
exclude = ["**/*.swp"]
""")

    builder = sdist.SdistBuilder.from_ini_path(pyproject)
    files = builder.apply_includes_excludes(builder.select_files())

    assert osp.join('pkg', '.main.swp') not in files
    assert osp.join('pkg', 'sub', '.editor.swp') not in files
    assert osp.join('pkg', 'module.py') in files
