import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from rewriter.fixers import Fixer
from rewriter.options import Options
from rewriter.parser import parse_tree, unparse_tree
from rewriter.trackers.imports import ImportTracker
from rewriter.trackers.stats import ChangeTracker
from rewriter.walker import Walker

__all__ = [
    "Fixer",
    "Options",
    "Walker",
    "ImportTracker",
    "ChangeTracker",
    "parse_tree",
    "unparse_tree",
]

COMPILED = Path(__file__).suffix in (".pyd", ".so")


def parse_options(args: Any = sys.argv[1:]) -> Options:
    is_compiled = "yes" if COMPILED else "no"
    parser = ArgumentParser(
        prog="rewriter", description=f"Rewrite python code (compiled: {is_compiled})"
    )
    parser.add_argument("filename", help="file to rewrite")
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="execute rewrite but don't update the original file",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="print diff changes")

    parsed_args: Any = parser.parse_args(args)
    opts: Options = parsed_args
    return opts


def main() -> None:
    opts = parse_options()
    tree = parse_tree(opts)

    change_tracker = ChangeTracker()
    import_tracker = ImportTracker(change_tracker)
    walker = Walker(opts, change_tracker, import_tracker)
    walker.walk(tree)

    unparse_tree(opts, tree, change_tracker, import_tracker)


if __name__ == "__main__":
    main()
