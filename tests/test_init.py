from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from flit import init

def test_store_defaults():
    with TemporaryDirectory() as td:
        with patch.object(init, 'get_data_dir', lambda : Path(td)):
            assert init.get_defaults() == {}
            d = {'author': 'Test'}
            init.store_defaults(d)
            assert init.get_defaults() == d
