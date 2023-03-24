import sys
from argparse import ArgumentParser
from typing import Any, Protocol


class Options(Protocol):
    filename: str
    source: str
    dry_run: bool
    verbose: bool


def parse_options(args: Any = sys.argv[1:]) -> Options:
    parser = ArgumentParser(prog="rewriter", description="Rewrite python code")
    parser.add_argument("filename")
    parser.add_argument("-d", "--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    parsed_args: Any = parser.parse_args(args)
    opts: Options = parsed_args
    return opts
