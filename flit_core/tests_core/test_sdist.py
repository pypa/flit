from io import BytesIO
import os.path as osp
from pathlib import Path
import tarfile
import unicodedata
import pytest
from testpath import assert_isfile

from flit_core import sdist


def _write_minimal_project(proj):
    pkg = proj / 'mypkg'
    pkg.mkdir(parents=True)
    (pkg / '__init__.py').write_text(
        '"""demo package."""\n__version__ = "0.0.1"\n'
    )
    (proj / 'pyproject.toml').write_text(
        "[build-system]\n"
        "requires = ['flit_core >=3.2,<4']\n"
        "build-backend = 'flit_core.buildapi'\n\n"
        "[project]\n"
        "name = 'mypkg'\n"
        "version = '0.0.1'\n"
        "description = 'demo'\n",
        encoding='utf-8',
    )
    return pkg

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


def test_filepatterns_unicode_normalisation(tmp_path):
    # CWE-176 / CWE-697: file selection must be normalisation-insensitive, so an
    # exclude/include rule still matches the same file when it is stored on disk
    # in a different Unicode normalisation form (as happens on macOS APFS/HFS+,
    # where glob() yields the rule's form but os.walk yields the on-disk form).
    nfc = unicodedata.normalize('NFC', 'café.txt')
    nfd = unicodedata.normalize('NFD', 'café.txt')
    assert nfc != nfd

    # File on disk under one form; glob() picks it up into the raw set as-is.
    (tmp_path / nfc).write_bytes(b'secret')
    pats = sdist.FilePatterns([nfc], str(tmp_path))
    assert nfc in pats.files  # raw on-disk form preserved (needed to open it)
    # A candidate walked in the *other* form must still match.
    assert pats.match_file(nfd) is True
    assert pats.match_file(nfc) is True

    # Same for directory patterns and the subdirectory-prefix check.
    nfc_dir = unicodedata.normalize('NFC', 'données')
    nfd_dir = unicodedata.normalize('NFD', 'données')
    (tmp_path / nfc_dir).mkdir()
    (tmp_path / nfc_dir / 'inner.txt').write_bytes(b'x')
    dpats = sdist.FilePatterns([nfc_dir], str(tmp_path))
    assert dpats.match_dir(nfd_dir) is True
    assert dpats.match_file(osp.join(nfd_dir, 'inner.txt')) is True


def test_apply_excludes_unicode_normalisation(tmp_path):
    # Integration-level regression for the macOS APFS scenario: the exclude rule
    # and the glob-built set are NFC, while the walk yields the file as NFD. The
    # secret must not survive into the selected file list. (ext4 glob/walk never
    # disagree on form, so we simulate APFS by feeding the walk result as NFD.)
    nfc = unicodedata.normalize('NFC', 'secret_café.txt')
    nfd = unicodedata.normalize('NFD', 'secret_café.txt')
    assert nfc != nfd

    pkg = tmp_path / 'mypkg'
    pkg.mkdir()
    (pkg / '__init__.py').write_text('"""demo package."""\n__version__ = "0.0.1"\n')
    (pkg / nfc).write_text('AWS_SECRET_ACCESS_KEY=AKIA_TOP_SECRET')  # on disk NFC
    (pkg / 'keep.txt').write_text('public\n')
    (tmp_path / 'pyproject.toml').write_text(
        "[build-system]\n"
        "requires = ['flit_core >=3.2,<4']\n"
        "build-backend = 'flit_core.buildapi'\n\n"
        "[project]\n"
        "name = 'mypkg'\n"
        "version = '0.0.1'\n"
        "description = 'demo'\n\n"
        "[tool.flit.sdist]\n"
        f"exclude = ['mypkg/{nfc}']\n",  # rule written NFC
        encoding='utf-8',
    )

    builder = sdist.SdistBuilder.from_ini_path(tmp_path / 'pyproject.toml')
    # Simulate the on-disk name being yielded by the walk in NFD form.
    walked = [
        osp.join('mypkg', nfd) if osp.basename(f) == nfc else f
        for f in builder.select_files()
    ]
    files = builder.apply_includes_excludes(walked)

    assert not any(
        unicodedata.normalize('NFC', osp.basename(f)) == nfc for f in files
    ), "NFD secret bypassed its NFC exclude rule"
    assert osp.join('mypkg', 'keep.txt') in files


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


@pytest.mark.parametrize('relpath, linkname, escapes', [
    (osp.join('mypkg', 'leak'), '/etc/passwd', True),            # absolute
    (osp.join('mypkg', 'leak'), osp.join('..', '..', 'secret'), True),  # climbs out
    (osp.join('mypkg', 'leak'), osp.join('..', 'sibling.py'), False),   # stays in tree
    (osp.join('mypkg', 'leak'), 'neighbour.py', False),          # same dir
    ('leak', 'pyproject.toml', False),                           # root-level, in tree
    ('leak', osp.join('..', 'outside'), True),                   # root-level escape
])
def test_symlink_target_escapes(relpath, linkname, escapes):
    assert sdist._symlink_target_escapes(relpath, linkname) is escapes


def test_sdist_rejects_external_symlink(tmp_path):
    # CWE-22 tar-slip: a symlink whose target escapes the project directory must
    # not be packed into the sdist, since on extraction it would point outside
    # the extraction root (arbitrary file read/overwrite on the consumer).
    outside = tmp_path / 'outside_secret.txt'
    outside.write_text('AWS_SECRET_ACCESS_KEY=AKIA_TOP_SECRET')

    proj = tmp_path / 'proj'
    pkg = _write_minimal_project(proj)
    (pkg / 'leak.txt').symlink_to(outside)  # escapes the project tree

    builder = sdist.SdistBuilder.from_ini_path(proj / 'pyproject.toml')
    with pytest.raises(Exception, match='outside the project directory'):
        builder.build(tmp_path / 'dist')


def test_sdist_allows_internal_symlink(tmp_path):
    # A symlink that stays within the project tree is fine and must still build.
    proj = tmp_path / 'proj'
    pkg = _write_minimal_project(proj)
    (pkg / 'real.txt').write_text('data')
    (pkg / 'link.txt').symlink_to('real.txt')  # relative, same directory

    builder = sdist.SdistBuilder.from_ini_path(proj / 'pyproject.toml')
    path = builder.build(tmp_path / 'dist')
    assert_isfile(path)
    with tarfile.open(path) as tar:
        names = {osp.basename(m.name) for m in tar.getmembers()}
    assert 'link.txt' in names
