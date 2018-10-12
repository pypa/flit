import pytest
from flit.common import InvalidVersion
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

    assert len(check('Bücher')) == 1
    assert len(check('requests 2.14')) == 1
    assert len(check('pexpect; sys.platform == "win32"')) == 1  # '.' -> '_'
    # Several problems in one requirement
    assert len(check('pexpect[_foo] =3; sys.platform == "win32"')) == 3

def test_validate_environment_marker():
    vem = fv.validate_environment_marker

    assert vem('python_version >= "3" and os_name == \'posix\'') == []
    assert vem("""extra == "test" and (os_name == "nt" or python_version == "2.7")""") == []
    assert vem("""(extra == "test") and (os_name == "nt" or python_version == "2.7")""") == []
    assert vem("""(extra == "test" and (os_name == "nt" or python_version == "2.7"))""") == []
    assert vem("""((((((((((extra == "test"))))))))))""") == []

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

    res = vem("""()))))()extra == "test"(((((((""")  # No chained comparisons
    assert len(res) == 1
    assert res[0] == 'Validation Error incorrect parentheses'

    res = vem("""extra == "test" and or (os_name == "nt" or python_version == "2.7")""")  # No chained comparisons
    assert len(res) == 1
    assert res[0] == """<class 'list'>: ['Invalid expression "and or"']"""

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

def test_normalise_version():
    nv = fv.normalise_version
    assert nv('4.3.1') == '4.3.1'
    assert nv('1.0b2') == '1.0b2'
    assert nv('2!1.3') == '2!1.3'

    # Prereleases
    assert nv('1.0B2') == '1.0b2'
    assert nv('1.0.b2') == '1.0b2'
    assert nv('1.0beta2') == '1.0b2'
    assert nv('1.01beta002') == '1.1b2'
    assert nv('1.0-preview2') == '1.0rc2'
    assert nv('1.0_c') == '1.0rc0'

    # Post releases
    assert nv('1.0post-2') == '1.0.post2'
    assert nv('1.0post') == '1.0.post0'
    assert nv('1.0-rev3') == '1.0.post3'
    assert nv('1.0-2') == '1.0.post2'

    # Development versions
    assert nv('1.0dev-2') == '1.0.dev2'
    assert nv('1.0dev') == '1.0.dev0'
    assert nv('1.0-dev3') == '1.0.dev3'

    assert nv('1.0+ubuntu-01') == '1.0+ubuntu.1'
    assert nv('v1.3-pre2') == '1.3rc2'
    assert nv(' 1.2.5.6\t') == '1.2.5.6'
    assert nv('1.0-alpha3-post02+ubuntu_xenial_5') == '1.0a3.post2+ubuntu.xenial.5'

    with pytest.raises(InvalidVersion):
        nv('3!')

    with pytest.raises(InvalidVersion):
        nv('abc')
