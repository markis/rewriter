from rewriter.fixers import Fixer
from rewriter.options import Options, parse_options
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
