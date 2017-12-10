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
