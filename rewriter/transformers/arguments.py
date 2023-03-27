import ast

from rewriter.trackers.changes import Change
from rewriter.trackers.imports import Import
from rewriter.transformers import TransformerReturnType, transformer

NAME_ANY = "Any"
NAME_CLS = "cls"
NAME_SELF = "self"


@transformer(ast.arguments)
def transform_args(node: ast.AST, parent: ast.AST, ctx: ast.AST) -> TransformerReturnType:
    changes: list[Change] = []
    imports: list[Import] = []

    if not isinstance(node, ast.arguments):
        return changes, imports

    def get_range(node: ast.arg) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno or node.lineno
        return (lineno, end_lineno)

    def transform_arg(node: ast.arg, _: ast.AST, ctx: ast.AST) -> None:
        if isinstance(ctx, ast.ClassDef) and node.arg in (NAME_CLS, NAME_SELF):
            return

        if not node.annotation:
            node.annotation = ast.Name(id=NAME_ANY)
            imports.append(Import("typing", "Any"))
            changes.append(Change(get_range(node), "missing-arg-type"))

    if node.vararg:
        transform_arg(node.vararg, parent, ctx)

    if node.kwarg:
        transform_arg(node.kwarg, parent, ctx)

    for arg in node.args:
        transform_arg(arg, parent, ctx)

    for arg in node.posonlyargs:
        transform_arg(arg, parent, ctx)

    for arg in node.kwonlyargs:
        transform_arg(arg, parent, ctx)

    return changes, imports
