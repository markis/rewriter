from argparse import ArgumentParser
from typing import Any, Protocol


class Options(Protocol):
    filename: str
    source: str
    dry_run: bool
    verbose: bool


def parse_options() -> Options:
    parser = ArgumentParser(prog="rewriter", description="Rewrite python code")
    parser.add_argument("filename")
    parser.add_argument("-d", "--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    args: Any = parser.parse_args()
    opts: Options = args
    return opts
