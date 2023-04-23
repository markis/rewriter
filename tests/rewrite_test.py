import ast
from textwrap import dedent
from unittest.mock import Mock

from syrupy.assertion import SnapshotAssertion

from rewriter.options import Options
from rewriter.parser import unparse_tree
from rewriter.transformers import transform
from rewriter.walker import walk


def rewrite_code(source: str) -> str:
    source = dedent(source).lstrip()
    mock_opts = Mock(spec=Options, filename="test.py", source=source, dry_run=True, verbose=True)
    tree = ast.parse(source)
    changes, imports = walk(transform, tree)
    return unparse_tree(mock_opts, tree, changes, imports)


def test_func_definition(snapshot: SnapshotAssertion) -> None:
    source = """
    def test(x, *args, **kwargs):
        pass
    """

    assert rewrite_code(source) == snapshot


def test_class_definition(snapshot: SnapshotAssertion) -> None:
    source = """
    class Test:
        def __init__(self, *, x):
            pass

        def do(self, x):
            return 1 / 2
    """

    assert rewrite_code(source) == snapshot
