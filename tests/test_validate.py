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
