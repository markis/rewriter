import ast
from collections.abc import Sequence
from typing import overload

from rewriter.options import Options
from rewriter.trackers.changes import ChangeTracker
from rewriter.trackers.imports import ImportTracker
from rewriter.transformers import Transformer, TransformMap

WalkableNodeType = ast.Module | ast.AST | Sequence[ast.AST]
EMPTY_AST: ast.AST = ast.AST()


class Walker:
    """
    Recursively walk the tree and fix all methods/arguments missing types
    """

    opts: Options
    changes: ChangeTracker
    imports: ImportTracker
    transformers: TransformMap

    def __init__(
        self,
        opts: Options,
        changes: ChangeTracker,
        imports: ImportTracker,
        transformers: TransformMap | None = None,
    ) -> None:
        self.opts = opts
        self.changes = changes
        self.imports = imports
        self.transformers = transformers or Transformer.get_transformers(opts, changes, imports)

    @overload
    def walk(self, node: ast.Module) -> None:
        ...

    @overload
    def walk(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: Sequence[ast.AST], parent: ast.AST, ctx: ast.AST) -> None:
        ...

    def walk(
        self, node: WalkableNodeType, parent: ast.AST = EMPTY_AST, ctx: ast.AST = EMPTY_AST
    ) -> None:
        if isinstance(node, Sequence):
            for n in node:
                self.walk(n, parent, ctx)
        else:
            if isinstance(node, ast.Module | ast.ClassDef):
                self.walk(node.body, node, node)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                self.walk(node.body, node, ctx)
                self.walk(node.args, node, ctx)
            elif hasattr(node, "body"):
                self.walk(getattr(node, "body"), parent, ctx)
            elif hasattr(node, "args"):
                self.walk(getattr(node, "args"), parent, ctx)

            for transformer in self.transformers[type(node)]:
                transformer.transform(node, parent, ctx)
