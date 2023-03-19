import ast
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from rewriter.options import Options

ASTType = type[ast.AST]
FixTypes = Sequence[ASTType]
FixerMap = Mapping[ASTType, Sequence["Fixer"]]
FixerStats = set["Stat"]


NAME_ANY = "Any"
NAME_NONE = "None"
NAME_CLS = "cls"
NAME_SELF = "self"
NAME_TYPING = "typing"
EMPTY_FIXER_STATS: FixerStats = set()


@dataclass(frozen=True)
class Stat:
    type: str
    range: tuple[int, int]
    fixed: ast.AST
    node: ast.AST


class Fixer(ABC):
    opts: Options

    def __init__(self, opts: Options) -> None:
        self.opts = opts

    @classmethod
    def get_fixers(cls, opts: Options) -> FixerMap:
        fixers = defaultdict(list)
        for fixer in cls.__subclasses__():
            for fixer_type in fixer.get_fix_types():
                fixers[fixer_type].append(fixer(opts))
        return fixers

    @classmethod
    @abstractmethod
    def get_fix_types(cls) -> FixTypes:
        raise NotImplementedError()

    @abstractmethod
    def fix(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> FixerStats:
        raise NotImplementedError()


class ArgumentFixer(Fixer):
    @classmethod
    def get_fix_types(cls) -> FixTypes:
        return [ast.arg]

    def fix(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> FixerStats:
        if isinstance(node, ast.arg):
            return self.fix_arg(node, parent, ctx)
        return EMPTY_FIXER_STATS

    def fix_arg(self, node: ast.arg, parent: ast.AST, ctx: ast.AST) -> FixerStats:
        if isinstance(ctx, ast.ClassDef) and node.arg in (NAME_CLS, NAME_SELF):
            return EMPTY_FIXER_STATS
        if node.annotation:
            return EMPTY_FIXER_STATS

        node.annotation = ast.Name(id=NAME_ANY)
        return {Stat(type="missing-arg-type", fixed=node, node=parent, range=self.get_range(node))}

    def get_range(self, node: ast.arg) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno
        return (lineno, end_lineno)


class ClassFixer(Fixer):
    NONE_METHODS = {"__init__"}

    @classmethod
    def get_fix_types(cls) -> FixTypes:
        return [ast.FunctionDef]

    def fix(self, node: ast.AST, _: ast.AST, ctx: ast.AST) -> FixerStats:
        if isinstance(node, ast.FunctionDef):
            return self.fix_func(node, ctx)
        return EMPTY_FIXER_STATS

    def fix_func(self, node: ast.FunctionDef, ctx: ast.AST) -> FixerStats:
        if isinstance(ctx, ast.ClassDef):
            if node.name in self.NONE_METHODS:
                node.returns = ast.Name(id=NAME_NONE, ctx=node)
                range = self.get_range(node)
                return {Stat(type="missing-return-type-none", range=range, fixed=node, node=node)}

        if not node.returns:
            node.returns = ast.Name(id=NAME_ANY, ctx=node)
            range = self.get_range(node)
            return {Stat(type="missing-return-type-any", range=range, fixed=node, node=node)}

        return EMPTY_FIXER_STATS

    def get_range(self, node: ast.FunctionDef) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno
        if node.body:
            end_lineno = node.body[0].lineno
        return (lineno, end_lineno)


# class ImportFixer:
#     typing_import_from: ast.ImportFrom | None = None
#     typing_import_from_has_ANY: bool = False
#     typing_import: ast.Import | None = None
#
#     def check_import(self, node: ast.ImportFrom | ast.Import) -> None:
#
#         if self.typing_import_from and self.typing_import_from_has_ANY:
#             return
#
#         if isinstance(node, ast.ImportFrom):
#             if node.module == NAME_TYPING:
#                 self.typing_import_from = node
#                 for name in node.names:
#                     if name.name == NAME_ANY:
#                         self.typing_import_from_has_ANY = True
#                         return
#         else:
#             for name in node.names:
#                 if name.name == NAME_TYPING:
#                     self.typing_import = node
#                     return
