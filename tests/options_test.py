import pytest

from rewriter import parse_options


def test_options_parsing() -> None:
    args = parse_options(["-d", "-v", "test.py"])

    assert args.dry_run
    assert args.verbose
    assert args.filename


def test_help() -> None:
    with pytest.raises(SystemExit):
        parse_options(["--help"])
        assert False, "Shouldn't make it here"
