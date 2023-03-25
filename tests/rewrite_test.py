import ast
from textwrap import dedent
from unittest.mock import Mock

from rewriter.options import Options
from rewriter.parser import unparse_tree
from rewriter.trackers.changes import ChangeTracker
from rewriter.trackers.imports import ImportTracker
from rewriter.walker import Walker


def format_str(source: str) -> str:
    return dedent(source).lstrip()


def generate_new_source(source: str) -> str:
    mock_opts = Mock(spec=Options, filename="test.py", source=source, dry_run=True, verbose=True)
    tree = ast.parse(source)
    change_tracker = ChangeTracker()
    import_tracker = ImportTracker(change_tracker)
    walker = Walker(mock_opts, change_tracker, import_tracker)
    walker.walk(tree)
    return unparse_tree(mock_opts, tree, change_tracker, import_tracker)


def test_func_definition() -> None:
    source = format_str(
        """
        from __future__ import annotations


        def test(x, *args, **kwargs):
            pass
        """
    )
    expected = format_str(
        """
        from __future__ import annotations
        from typing import Any


        def test(x: Any, *args: Any, **kwargs: Any) -> None:
            pass
        """
    )

    assert generate_new_source(source) == expected


def test_class_definition() -> None:
    source = format_str(
        """
        from __future__ import annotations


        class Test:
            def __init__(self, *, x):
                pass

            def do(self, x):
                return 1 / 2
        """
    )
    expected = format_str(
        """
        from __future__ import annotations
        from typing import Any


        class Test:
            def __init__(self, *, x: Any) -> None:
                pass

            def do(self, x: Any) -> Any:
                return 1 / 2
        """
    )

    assert generate_new_source(source) == expected
