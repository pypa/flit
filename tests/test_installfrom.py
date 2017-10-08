import pytest
from flit.installfrom import (
    parse_address, InvalidAddress, UnknownAddressType, InvalidAddressLocation
)

def test_parse_address():
    atype, loc = parse_address(__file__)
    assert atype == 'local_file'

    atype, loc = parse_address('https://example.com')
    assert atype == 'url'

    with pytest.raises(InvalidAddress):
        parse_address('foobar')

    with pytest.raises(UnknownAddressType):
        # glithub instead of github
        parse_address('glithub:takluyver/flit')

    with pytest.raises(InvalidAddressLocation):
        parse_address('github:takluyver')

    atype, loc = parse_address('github:takluyver/flit')
    assert atype == 'github'
