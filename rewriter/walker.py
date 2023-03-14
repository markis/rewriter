import ast
from collections.abc import Sequence
from typing import overload


NAME_ANY = "Any"
NAME_NONE = "None"
NAME_SELF = "self"
NAME_TYPING = "typing"
NAMES_DUNDER = {"__init__"}
EMPTY_AST: ast.AST = ast.AST()


class Walker:
    """
    Recursively walk the tree and fix all methods/arguments missing with Any
    """

    root: ast.Module
    filename: str
    typing_import_from: ast.ImportFrom | None = None
    typing_import_from_has_ANY: bool = False
    typing_import: ast.Import | None = None
    stats: list[str] = []

    def __init__(self, filename: str, root: ast.Module) -> None:
        self.filename = filename
        self.root = root

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
        Recursively walk the tree and fix all methods/arguments missing with Any
        """
        if node is EMPTY_AST:
            node = self.root

        if isinstance(node, Sequence):
            for n in node:
                self.walk(n, ctx)
        elif isinstance(node, (ast.Module, ast.ClassDef)):
            self.walk(node.body, node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            self.check_import(node)
        elif isinstance(node, ast.FunctionDef):
            self.walk(node.body, ctx)
            self.walk(node.args, ctx)
            self.fix_funcdef(node, ctx)
        elif isinstance(node, ast.arguments):
            self.walk(node.args, ctx)
        elif isinstance(node, ast.arg):
            self.fix_arg(node, ctx)
        elif isinstance(node, ast.Pass):
            pass
        else:
            # print(type(node))
            # print(node.__dict__)
            pass

    def generate_annotation(self, arg: ast.arg) -> ast.Name:
        self.stats.append(f"Missing arg type - {arg.arg}: {arg.lineno}")
        if self.typing_import_from_has_ANY:
            return ast.Name(id=NAME_ANY)
        elif self.typing_import_from is not None:
            self.typing_import_from.names.insert(0, ast.alias(name=NAME_ANY))
            self.typing_import_from_has_ANY = True
            return ast.Name(id=NAME_ANY)
        else:
            return ast.Name(id=NAME_ANY)

    def check_import(self, node: ast.ImportFrom | ast.Import) -> None:
        if self.typing_import_from and self.typing_import_from_has_ANY:
            return

        if isinstance(node, ast.ImportFrom):
            if node.module == NAME_TYPING:
                self.typing_import_from = node
                for name in node.names:
                    if name.name == NAME_ANY:
                        self.typing_import_from_has_ANY = True
                        return
        else:
            for name in node.names:
                if name.name == NAME_TYPING:
                    self.typing_import = node
                    return

    def fix_arg(self, arg: ast.arg, ctx: ast.AST) -> None:
        if isinstance(ctx, ast.ClassDef):
            if arg.arg == NAME_SELF:
                return

        if not arg.annotation:
            arg.annotation = self.generate_annotation(arg)

    def fix_funcdef(self, func: ast.FunctionDef, ctx: ast.AST) -> None:
        if isinstance(ctx, ast.ClassDef):
            if func.name in NAMES_DUNDER:
                func.returns = ast.Name(id=NAME_NONE, ctx=func)
                return

        if not func.returns:
            self.stats.append(f"Missing return - {func.name}: {func.lineno}")
            func.returns = ast.Name(id=NAME_ANY, ctx=func)
