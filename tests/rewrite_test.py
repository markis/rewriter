import ast
from textwrap import dedent
from typing import Any
from unittest.mock import Mock

from syrupy.assertion import SnapshotAssertion

from rewriter.options import Options
from rewriter.parser import unparse_tree
from rewriter.transformers import transform
from rewriter.walker import walk


def format_str(source: str) -> str:
    return dedent(source).lstrip()


def generate_new_source(source: str) -> str:
    mock_opts = Mock(spec=Options, filename="test.py", source=source, dry_run=True, verbose=True)
    tree = ast.parse(source)

    changes, imports = walk(transform, tree)

    return unparse_tree(mock_opts, tree, changes, imports)


def test_func_definition(snapshot: SnapshotAssertion) -> None:
    source = format_str(
        """
        def test(x, *args, **kwargs):
            pass
        """
    )

    assert generate_new_source(source) == snapshot


def test_class_definition(snapshot: Any) -> None:
    source = format_str(
        """
        class Test:
            def __init__(self, *, x):
                pass

            def do(self, x):
                return 1 / 2
        """
    )

    assert generate_new_source(source) == snapshot
