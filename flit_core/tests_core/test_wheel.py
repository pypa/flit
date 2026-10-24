import os
import stat
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from testpath import assert_isfile

from flit_core.wheel import make_wheel_in, main

samples_dir = Path(__file__).parent / 'samples'


def _mkdir(p):
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_pkg_project(proj):
    pkg = proj / 'mypkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text('"""pkg."""\n__version__ = "0.1"\n')
    (proj / 'pyproject.toml').write_text(
        "[build-system]\n"
        "requires = ['flit_core >=3.2,<4']\n"
        "build-backend = 'flit_core.buildapi'\n\n"
        "[project]\n"
        "name = 'mypkg'\n"
        "version = '0.1'\n"
        "description = 'x'\n",
        encoding='utf-8',
    )
    return pkg


def test_wheel_rejects_escaping_symlink(tmp_path):
    # CWE-22/CWE-59: a symlink in the package pointing outside the project must
    # not have its (host file) contents copied into the wheel.
    secret = tmp_path / 'secret.txt'
    secret.write_text('AWS_SECRET_ACCESS_KEY=AKIA_TOP_SECRET')
    proj = tmp_path / 'proj'
    pkg = _write_pkg_project(proj)
    (pkg / 'leak.txt').symlink_to(secret)
    with pytest.raises(Exception, match='outside the project'):
        make_wheel_in(proj / 'pyproject.toml', _mkdir(tmp_path / 'dist'))


def test_wheel_allows_in_tree_symlink(tmp_path):
    proj = tmp_path / 'proj'
    pkg = _write_pkg_project(proj)
    (pkg / 'real.txt').write_text('data')
    (pkg / 'link.txt').symlink_to('real.txt')  # relative, in-tree
    info = make_wheel_in(proj / 'pyproject.toml', _mkdir(tmp_path / 'dist'))
    assert_isfile(info.file)
    with ZipFile(info.file, 'r') as zf:
        assert 'mypkg/link.txt' in zf.namelist()


def test_licenses_dir(tmp_path):
    # Smoketest for https://github.com/pypa/flit/issues/399
    info = make_wheel_in(samples_dir / 'inclusion' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)


def test_source_date_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv('SOURCE_DATE_EPOCH', '1633007882')
    info = make_wheel_in(samples_dir / 'pep621' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    # Minimum value for zip timestamps is 1980-1-1
    with ZipFile(info.file, 'r') as zf:
        assert zf.getinfo('module1a.py').date_time[:3] == (2021, 9, 30)


def test_zero_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv('SOURCE_DATE_EPOCH', '0')
    info = make_wheel_in(samples_dir / 'pep621' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    # Minimum value for zip timestamps is 1980-1-1
    with ZipFile(info.file, 'r') as zf:
        assert zf.getinfo('module1a.py').date_time == (1980, 1, 1, 0, 0, 0)


def test_main(tmp_path):
    main(['--outdir', str(tmp_path), str(samples_dir / 'pep621')])
    wheels = list(tmp_path.glob('*.whl'))
    assert len(wheels) == 1
    # Minimum value for zip timestamps is 1980-1-1
    with ZipFile(wheels[0], 'r') as zf:
        assert 'module1a.py' in zf.namelist()


def test_data_dir(tmp_path):
    info = make_wheel_in(samples_dir / 'with_data_dir' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    with ZipFile(info.file, 'r') as zf:
        assert 'module1-0.1.data/data/share/man/man1/foo.1' in zf.namelist()


def test_license_files(tmp_path):
    info = make_wheel_in(samples_dir / 'pep621_license_files' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    with ZipFile(info.file, 'r') as zf:
        assert 'module1-0.1.dist-info/licenses/LICENSE' in zf.namelist()
        assert 'module1-0.1.dist-info/licenses/module/vendor/LICENSE_VENDOR' in zf.namelist()


@pytest.mark.skipif(sys.platform == 'win32', reason='Windows does not have Unix file permissions')
def test_wheel_file_permissions(tmp_path):
    # mkstemp(), which is used to create the wheel before it's renamed to
    # its final name, creates files with mode 0600. The built wheel file
    # itself should not be left that restrictive. Regression test for
    # https://github.com/pypa/flit/issues/804
    info = make_wheel_in(samples_dir / 'pep621' / 'pyproject.toml', tmp_path)
    assert_isfile(info.file)
    mode = stat.S_IMODE(os.stat(info.file).st_mode)
    assert mode & 0o777 == 0o644, oct(mode)
