import ast
from textwrap import dedent

from rewriter.walker import AnyWalker


def format_str(source: str) -> str:
    return dedent(source).strip()


def generate_new_source(source: str) -> str:
    tree = ast.parse(source)
    AnyWalker(tree).walk()
    return ast.unparse(tree)


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

            def __init__(self, x):
                pass

            def do(self, x):
                pass
        """
    )
    expected = format_str(
        """
        class Test:

            def __init__(self, x: Any) -> None:
                pass

            def do(self, x: Any) -> Any:
                pass
        """
    )

    assert generate_new_source(source) == expected
