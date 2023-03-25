import ast
from collections.abc import Sequence
from typing import overload

from rewriter.fixers import Fixer, FixerMap
from rewriter.options import Options
from rewriter.trackers.imports import ImportTracker
from rewriter.trackers.stats import EMPTY_AST, ChangeTracker


class Walker:
    """
    Recursively walk the tree and fix all methods/arguments missing types
    """

    opts: Options
    fixers: FixerMap
    change_tracker: ChangeTracker
    import_tracker: ImportTracker

    def __init__(
        self,
        opts: Options,
        change_tracker: ChangeTracker,
        import_tracker: ImportTracker,
        fixers: FixerMap | None = None,
    ) -> None:
        self.opts = opts
        self.change_tracker = change_tracker
        self.import_tracker = import_tracker
        if not fixers:
            fixers = Fixer.get_fixers(opts, change_tracker, import_tracker)
        self.fixers = fixers

    @overload
    def walk(self, node: ast.AST, parent: ast.AST = EMPTY_AST, ctx: ast.AST = EMPTY_AST) -> None:
        ...

    @overload
    def walk(
        self, node: list[ast.AST], parent: ast.AST = EMPTY_AST, ctx: ast.AST = EMPTY_AST
    ) -> None:
        ...

    @overload
    def walk(
        self, node: list[ast.stmt], parent: ast.AST = EMPTY_AST, ctx: ast.AST = EMPTY_AST
    ) -> None:
        ...

    @overload
    def walk(
        self, node: list[ast.arg], parent: ast.AST = EMPTY_AST, ctx: ast.AST = EMPTY_AST
    ) -> None:
        ...

    def walk(
        self,
        node: ast.AST | list[ast.AST] | list[ast.stmt] | list[ast.arg],
        parent: ast.AST = EMPTY_AST,
        ctx: ast.AST = EMPTY_AST,
    ) -> None:
        """
        Recursively walk the tree
        """
        if self.import_tracker.current_imports is None and isinstance(node, ast.Module):
            self.import_tracker.track_current_imports(node)

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

            for fixer in self.fixers[type(node)]:
                fixer.fix(node, parent, ctx)
