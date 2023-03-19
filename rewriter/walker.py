import ast
from collections.abc import Sequence
from typing import overload

from rewriter.fixers import Fixer, FixerMap, FixerStats
from rewriter.options import Options

EMPTY_AST: ast.AST = ast.AST()


class Walker:
    """
    Recursively walk the tree and fix all methods/arguments missing types
    """

    root: ast.Module
    opts: Options
    stats: FixerStats = set()
    fixers: FixerMap
    edges: list[ast.AST] = []

    def __init__(self, opts: Options, root: ast.Module, fixers: FixerMap | None = None) -> None:
        self.opts = opts
        self.root = root
        if not fixers:
            fixers = Fixer.get_fixers(opts)
        self.fixers = fixers

    @overload
    def walk(self) -> None:
        ...

    @overload
    def walk(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: list[ast.AST], parent: ast.AST, ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: list[ast.stmt], parent: ast.AST, ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: list[ast.arg], parent: ast.AST, ctx: ast.AST) -> None:
        ...

    def walk(
        self,
        node: ast.AST | list[ast.AST] | list[ast.stmt] | list[ast.arg] = EMPTY_AST,
        parent: ast.AST = EMPTY_AST,
        ctx: ast.AST = EMPTY_AST,
    ) -> None:
        """
        Recursively walk the tree
        """
        if node is EMPTY_AST:
            node = self.root

        if isinstance(node, Sequence):
            for n in node:
                self.walk(n, parent, ctx)
        else:
            if isinstance(node, ast.Module | ast.ClassDef):
                self.walk(node.body, node, node)
            elif isinstance(node, ast.FunctionDef):
                self.walk(node.body, node, ctx)
                self.walk(node.args, node, ctx)
            elif isinstance(node, ast.With | ast.For | ast.If):
                self.walk(node.body, parent, ctx)
            elif isinstance(node, ast.arguments):
                self.walk(node.args, parent, ctx)
            else:
                self.edges.append(node)

            results = self.process_fixers(node, parent, ctx)
            self.collect_stats(results)

    def process_fixers(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> FixerStats:
        results: FixerStats = set()
        for fixer in self.fixers[type(node)]:
            results.update(fixer.fix(node, parent, ctx))
        return results

    def collect_stats(self, stats: FixerStats) -> None:
        self.stats.update(stats)
