import ast
from collections.abc import Sequence
from itertools import chain
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
            result = merge(result, walk(transform, n, parent, ctx))
    else:
        if isinstance(node, ast.Module | ast.ClassDef):
            result = merge(result, walk(transform, node.body, node, node))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            result = merge(result, walk(transform, node.body, node, ctx))
            result = merge(result, walk(transform, node.args, node, ctx))
        elif hasattr(node, "body"):
            result = merge(result, walk(transform, getattr(node, "body"), parent, ctx))
        elif hasattr(node, "args"):
            result = merge(result, walk(transform, getattr(node, "args"), parent, ctx))

        for new_result in transform(node, parent, ctx):
            result = merge(result, new_result)

    return result


def merge(
    result: TransformerReturnType,
    new_result: TransformerReturnType,
) -> TransformerReturnType:
    changes, imports = result
    new_changes, new_imports = new_result

    if new_changes:
        changes = chain(changes, new_changes)
    if new_imports:
        imports = chain(imports, new_imports)

    return (changes, imports)
