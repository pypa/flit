import pytest

from flit import main


def test_help_mentions_the_correct_filename(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["flit", "--help"])
    with pytest.raises(SystemExit, match="^0$") as cm:
        main()
    assert cm.value.args == (0,)
    out, err = capsys.readouterr()
    line = "    init                Prepare pyproject.toml for a new package\n"
    assert line in out
