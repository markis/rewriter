import ast
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence

from rewriter.options import Options

NAME_ANY = "ast.AST"
NAME_NONE = "None"
NAME_SELF = "self"
NAME_TYPING = "typing"


class Fixer(ABC):
    opts: Options

    def __init__(self, opts: Options) -> None:
        self.opts = opts

    @classmethod
    def get_fixers(cls, opts: Options) -> dict[type[ast.AST], list["Fixer"]]:
        fixers: dict[type[ast.AST], list["Fixer"]] = defaultdict(list)
        for fixer in cls.__subclasses__():
            for fixer_type in fixer.get_fix_types():
                fixers[fixer_type].append(fixer(opts))
        return fixers

    @classmethod
    @abstractmethod
    def get_fix_types(cls) -> Sequence[type[ast.AST]]:
        raise NotImplementedError()

    @abstractmethod
    def fix(self, node: ast.AST, ctx: ast.AST) -> list[str]:
        raise NotImplementedError()


class ArgumentFixer(Fixer):
    @classmethod
    def get_fix_types(cls) -> Sequence[type[ast.AST]]:
        return [ast.arg]

    def fix(self, node: ast.AST, ctx: ast.AST) -> list[str]:
        if not isinstance(node, ast.arg):
            return []
        if isinstance(ctx, ast.ClassDef) and node.arg == NAME_SELF:
            return []
        if node.annotation:
            return []

        node.annotation = self.generate_annotation()
        return [f"Missing arg type - {node.arg}: {node.lineno}"]

    def generate_annotation(self) -> ast.Name:
        return ast.Name(id=NAME_ANY)


class ClassFixer(Fixer):
    NONE_METHODS = {"__init__"}

    @classmethod
    def get_fix_types(cls) -> Sequence[type[ast.AST]]:
        return [ast.FunctionDef]

    def fix(self, node: ast.AST, ctx: ast.AST) -> list[str]:
        if not isinstance(node, ast.FunctionDef):
            return []

        if isinstance(ctx, ast.ClassDef):
            if node.name in self.NONE_METHODS:
                node.returns = ast.Name(id=NAME_NONE, ctx=node)
                return [f"Missing return - {node.name}: {node.lineno}"]

        if not node.returns:
            node.returns = ast.Name(id=NAME_ANY, ctx=node)
            return [f"Missing return - {node.name}: {node.lineno}"]

        return []


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
