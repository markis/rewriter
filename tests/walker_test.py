import ast
from textwrap import dedent
from unittest import skip
from unittest.mock import Mock

from rewriter.options import Options
from rewriter.parser import unparse_tree
from rewriter.trackers.imports import ImportTracker
from rewriter.trackers.stats import ChangeTracker
from rewriter.walker import Walker


def format_str(source: str) -> str:
    return dedent(source)


def generate_new_source(source: str) -> str:
    mock_opts = Mock(spec=Options, filename="test.py", source=source, dry_run=True)
    tree = ast.parse(source)
    change_tracker = ChangeTracker()
    import_tracker = ImportTracker(change_tracker)
    walker = Walker(mock_opts, change_tracker, import_tracker)
    walker.walk(tree)
    return unparse_tree(mock_opts, tree, change_tracker, import_tracker)


@skip("working on it")
def test_func_definition() -> None:
    source = format_str(
        """
        def test(x):
            pass
        """
    )
    expected = format_str(
        """
        def test(x: Any) -> Any:
            pass
        """
    )

    assert generate_new_source(source) == expected


def test_class_definition() -> None:
    source = format_str(
        """
        class Test:
            def do(self, x):
                return 1 / 2
        """
    )
    expected = format_str(
        """
        class Test:
            def do(self, x) -> float:
                return 1 / 2
        """
    )

    assert generate_new_source(source) == expected
