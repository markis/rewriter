import ast
from collections.abc import Sequence
from typing import overload

from rewriter.trackers.changes import Change
from rewriter.trackers.imports import Import
from rewriter.transformers import Transform, TransformerReturnType

WalkableNodeType = ast.Module | ast.AST | Sequence[ast.AST]
EMPTY_AST: ast.AST = ast.AST()


def walk(tree: ast.Module, transform: Transform) -> TransformerReturnType:
    changes: list[Change] = []
    imports: list[Import] = []

    @overload
    def walker(node: ast.Module) -> None:
        ...

    @overload
    def walker(node: ast.AST, parent: ast.AST, ctx: ast.AST) -> None:
        ...

    @overload
    def walker(node: Sequence[ast.AST], parent: ast.AST, ctx: ast.AST) -> None:
        ...

    def walker(
        node: WalkableNodeType, parent: ast.AST = EMPTY_AST, ctx: ast.AST = EMPTY_AST
    ) -> None:
        if isinstance(node, Sequence):
            for n in node:
                walker(n, parent, ctx)
        else:
            if isinstance(node, ast.Module | ast.ClassDef):
                walker(node.body, node, node)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                walker(node.body, node, ctx)
                walker(node.args, node, ctx)
            elif hasattr(node, "body"):
                walker(getattr(node, "body"), parent, ctx)
            elif hasattr(node, "args"):
                walker(getattr(node, "args"), parent, ctx)

            for new_changes, new_imports in transform(node, parent, ctx):
                changes.extend(new_changes)
                imports.extend(new_imports)

    walker(tree)
    return changes, imports
