import ast
from collections.abc import Sequence
from typing import overload

from rewriter.transformers import Transform, TransformerReturnType

__all__ = ["walk"]

WalkableNodeType = ast.Module | ast.AST | Sequence[ast.AST]
EMPTY_AST: ast.AST = ast.AST()


@overload
def walk(transform: Transform, node: ast.Module) -> TransformerReturnType:
    ...


@overload
def walk(
    transform: Transform, node: ast.AST, parent: ast.AST, ctx: ast.AST
) -> TransformerReturnType:
    ...


@overload
def walk(
    transform: Transform, node: Sequence[ast.AST], parent: ast.AST, ctx: ast.AST
) -> TransformerReturnType:
    ...


def walk(
    transform: Transform,
    node: WalkableNodeType,
    parent: ast.AST = EMPTY_AST,
    ctx: ast.AST = EMPTY_AST,
) -> TransformerReturnType:
    result: TransformerReturnType = ([], [])
    if isinstance(node, Sequence):
        for n in node:
            merge(result, walk(transform, n, parent, ctx))
    else:
        if isinstance(node, ast.Module | ast.ClassDef):
            merge(result, walk(transform, node.body, node, node))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            merge(result, walk(transform, node.body, node, ctx))
            merge(result, walk(transform, node.args, node, ctx))
        elif hasattr(node, "body"):
            merge(result, walk(transform, getattr(node, "body"), parent, ctx))
        elif hasattr(node, "args"):
            merge(result, walk(transform, getattr(node, "args"), parent, ctx))

        for new_result in transform(node, parent, ctx):
            merge(result, new_result)

    return result


def merge(
    result: TransformerReturnType,
    new_result: TransformerReturnType,
) -> None:
    changes, imports = result
    new_changes, new_imports = new_result
    if new_changes:
        changes.extend(new_changes)
    if new_imports:
        imports.extend(new_imports)
