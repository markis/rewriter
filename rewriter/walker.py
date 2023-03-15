import ast
from collections.abc import Sequence
from pprint import pprint
from typing import overload

from rewriter.fixers import Fixer
from rewriter.options import Options

EMPTY_AST: ast.AST = ast.AST()


class Walker:
    """
    Recursively walk the tree and fix all methods/arguments missing types
    """

    root: ast.Module
    opts: Options
    stats: list[str] = []
    fixers: dict[type[ast.AST], list[Fixer]]
    edges: list[ast.AST] = []

    def __init__(self, opts: Options, root: ast.Module) -> None:
        self.opts = opts
        self.root = root
        self.fixers = Fixer.get_fixers(opts)

    @overload
    def walk(self) -> None:
        ...

    @overload
    def walk(self, node: ast.AST, ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: list[ast.AST], ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: list[ast.stmt], ctx: ast.AST) -> None:
        ...

    @overload
    def walk(self, node: list[ast.arg], ctx: ast.AST) -> None:
        ...

    def walk(
        self,
        node: ast.AST | list[ast.AST] | list[ast.stmt] | list[ast.arg] = EMPTY_AST,
        ctx: ast.AST = EMPTY_AST,
    ) -> None:
        """
        Recursively walk the tree
        """
        if node is EMPTY_AST:
            node = self.root

        if isinstance(node, Sequence):
            for n in node:
                self.walk(n, ctx)
        else:
            if isinstance(node, (ast.Module, ast.ClassDef)):
                self.walk(node.body, node)
            elif isinstance(node, ast.FunctionDef):
                self.walk(node.body, ctx)
                self.walk(node.args, ctx)
            elif isinstance(node, ast.arguments):
                self.walk(node.args, ctx)
            else:
                self.edges.append(node)

            results = self.process_fixers(node, ctx)
            self.gather_stats(results)

    def gather_stats(self, stats: list[str]) -> None:
        self.stats.extend(stats)

    def print_stats(self) -> None:
        if self.stats:
            pprint(self.opts.filename)
            pprint(self.stats)

    def process_fixers(self, node: ast.AST, ctx: ast.AST) -> list[str]:
        results: list[str] = []
        for fixer in self.fixers[type(node)]:
            results.extend(fixer.fix(node, ctx))
        return results
