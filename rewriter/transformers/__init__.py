import ast
from collections import defaultdict
from collections.abc import Callable, MutableSequence
from typing import Protocol

from rewriter.trackers.changes import Change
from rewriter.trackers.imports import Import

AST = ast.AST
ASTType = type[AST]
TransformerReturnType = tuple[MutableSequence[Change], MutableSequence[Import]]
Transformer = Callable[[AST, AST, AST], TransformerReturnType]
TransformerProcessor = Callable[[AST, AST, AST], MutableSequence[TransformerReturnType]]
Transform = Callable[[AST, AST, AST], MutableSequence[TransformerReturnType]]

NAME_ANY = "Any"
NAME_BOOL = "bool"
NAME_INT = "int"
NAME_NONE = "None"
NAME_STR = "str"
NAME_CLS = "cls"
NAME_SELF = "self"
NAME_TYPING = "typing"


class TransformerDecorator(Protocol):
    def __call__(self, *args: ASTType) -> Callable[[Transformer], None]:
        ...


def make_transformer_registrar() -> tuple[TransformerDecorator, Transform]:
    registry = defaultdict(list)

    def transformer(*types: ASTType) -> Callable[[Transformer], None]:
        def wrapper(func: Transformer) -> None:
            for t in types:
                registry[t].append(func)

        return wrapper

    def transform(node: AST, parent: AST, ctx: AST) -> MutableSequence[TransformerReturnType]:
        return [func(node, parent, ctx) for func in registry[type(node)]]

    return transformer, transform


transformer, transform = make_transformer_registrar()


@transformer(ast.arguments)
def transform_args(node: AST, parent: AST, ctx: AST) -> TransformerReturnType:
    changes: list[Change] = []
    imports: list[Import] = []

    if not isinstance(node, ast.arguments):
        return changes, imports

    def get_range(node: ast.arg) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno or node.lineno
        return (lineno, end_lineno)

    def transform_arg(node: ast.arg, _: AST, ctx: AST) -> None:
        if isinstance(ctx, ast.ClassDef) and node.arg in (NAME_CLS, NAME_SELF):
            return

        if not node.annotation:
            node.annotation = ast.Name(id=NAME_ANY)
            imports.append(("typing", "Any"))
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


METHODS_MAP = [
    ("None", {"__init__"}),
    ("bool", {"__lt__", "__le__", "__ne__", "__eq__", "__gt__", "__ge__", "__bool__"}),
    ("int", {"__hash__"}),
    ("Self", {"__new__"}),
    ("str", {"__str__", "__repr__"}),
]
UNKNOWN_RETURN: list[ast.Return | ast.Yield | ast.YieldFrom] = []


@transformer(ast.FunctionDef, ast.AsyncFunctionDef)
def transform_func(node: AST, _: AST, ctx: AST) -> TransformerReturnType:
    def get_range(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno or node.lineno
        if node.body:
            end_lineno = node.body[0].lineno
        return (lineno, end_lineno)

    def guess_return_type(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        ctx: AST,
    ) -> ast.expr:
        returns = get_returns(node)
        if returns is UNKNOWN_RETURN:
            return ast.Name(id=NAME_ANY, ctx=node)
        elif len(returns) == 0:
            return ast.Name(id=NAME_NONE, ctx=node)
        elif (  # if only 1 return and it's a call to a class, we can assume it as the type
            len(returns) == 1
            and isinstance(returns[0], ast.Return)
            and isinstance(returns[0].value, ast.Call)
            and isinstance(returns[0].value.func, ast.Name)
            and returns[0].value.func.id[0].isupper()
            and "_" not in returns[0].value.func.id
        ):
            name = returns[0].value.func.id
            if isinstance(ctx, ast.ClassDef) and ctx.name == name:
                return ast.Constant(value=name)
            else:
                return ast.Name(id=name, ctx=node)
        elif len(returns) == 1:
            # print(self.opts.filename)
            # print(returns[0].value.__dict__)
            return ast.Name(id=NAME_ANY, ctx=node)
        else:
            return ast.Name(id=NAME_ANY, ctx=node)

    def get_returns(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[ast.Return | ast.Yield | ast.YieldFrom]:
        try:
            visitor = ReturnVisitor()
            visitor.visit(node)
            return visitor.returns
        except RecursionError:
            return UNKNOWN_RETURN

    changes: list[Change] = []
    imports: list[Import] = []
    if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
        return changes, imports

    if isinstance(ctx, ast.ClassDef):
        for name, methods in METHODS_MAP:
            if node.name in methods and not node.returns:
                if name == "Self":
                    node.returns = ast.Name(id=ast.Constant(ctx.name), ctx=node)
                else:
                    node.returns = ast.Name(id=name, ctx=node)
                imports.append(("typing", "Any"))
                changes.append(Change(get_range(node), f"missing-return-type-{name.lower()}"))

    if not node.returns:
        node.returns = guess_return_type(node, ctx)
        imports.append(("typing", "Any"))
        changes.append(Change(get_range(node), "missing-return-type-any"))

    return changes, imports


class ReturnVisitor(ast.NodeVisitor):
    returns: list[ast.Return | ast.Yield | ast.YieldFrom] = []

    def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
        self.returns.append(node)

    def visit_Yield(self, node: ast.Yield) -> None:  # noqa: N802
        self.returns.append(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:  # noqa: N802
        self.returns.append(node)


# class TransformerBase(ABC):
#     opts: Options
#     imports: ImportTracker
#     changes: ChangeTracker
#
#     def __init__(self, opts: Options, changes: ChangeTracker, imports: ImportTracker) -> None:
#         self.opts = opts
#         self.imports = imports
#         self.changes = changes
#
#     @classmethod
#     def get_transformers(
#         cls, opts: Options, changes: ChangeTracker, imports: ImportTracker
#     ) -> TransformMap:
#         fixers = defaultdict(list)
#         for fixer in cls.__subclasses__():
#             for fixer_type in fixer.get_transform_types():
#                 fixers[fixer_type].append(fixer(opts, changes, imports))
#         return fixers
#
#     @classmethod
#     @abstractmethod
#     def get_transform_types(cls) -> TransformTypes:
#         raise NotImplementedError()
#
#     @abstractmethod
#     def transform(self, node: AST, parent: AST, ctx: AST) -> None:
#         raise NotImplementedError()
#
#
# class ArgumentTransformer(TransformerBase):
#     @classmethod
#     def get_transform_types(cls) -> TransformTypes:
#         return [ast.arguments]
#
#     def transform(self, node: AST, parent: AST, ctx: AST) -> None:
#         if isinstance(node, ast.arguments):
#             self.transform_args(node, parent, ctx)
#
#     def transform_args(self, node: ast.arguments, parent: AST, ctx: AST) -> None:
#         if node.vararg:
#             self.transform_arg(node.vararg, parent, ctx)
#
#         if node.kwarg:
#             self.transform_arg(node.kwarg, parent, ctx)
#
#         for arg in node.args:
#             self.transform_arg(arg, parent, ctx)
#
#         for arg in node.posonlyargs:
#             self.transform_arg(arg, parent, ctx)
#
#         for arg in node.kwonlyargs:
#             self.transform_arg(arg, parent, ctx)
#
#     def transform_arg(self, node: ast.arg, _: AST, ctx: AST) -> None:
#         if isinstance(ctx, ast.ClassDef) and node.arg in (NAME_CLS, NAME_SELF):
#             return
#
#         if not node.annotation:
#             node.annotation = ast.Name(id=NAME_ANY)
#             self.imports.add_import("Any", "typing")
#             self.changes.add_change("missing-arg-type", self.get_range(node))
#
#     def get_range(self, node: ast.arg) -> tuple[int, int]:
#         lineno = node.lineno
#         end_lineno = node.end_lineno or node.lineno
#         return (lineno, end_lineno)


# class ClassTransformer(TransformerBase):
#     METHODS_MAP = [
#         ("None", {"__init__"}),
#         ("bool", {"__lt__", "__le__", "__ne__", "__eq__", "__gt__", "__ge__", "__bool__"}),
#         ("int", {"__hash__"}),
#         ("Self", {"__new__"}),
#         ("str", {"__str__", "__repr__"}),
#     ]
#     UNKNOWN_RETURN: list[ast.Return | ast.Yield | ast.YieldFrom] = []
#
#     @classmethod
#     def get_transform_types(cls) -> TransformTypes:
#         return [ast.FunctionDef, ast.AsyncFunctionDef]
#
#     def transform(self, node: AST, _: AST, ctx: AST) -> None:
#         if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
#             self.transform_func(node, ctx)
#
#     def transform_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, ctx: AST) -> None:
#         if isinstance(ctx, ast.ClassDef):
#             for name, methods in self.METHODS_MAP:
#                 if node.name in methods and not node.returns:
#                     if name == "Self":
#                         node.returns = ast.Name(id=ast.Constant(ctx.name), ctx=node)
#                     else:
#                         node.returns = ast.Name(id=name, ctx=node)
#                     range = self.get_range(node)
#                     self.imports.add_import("Any", "typing")
#                     self.changes.add_change(f"missing-return-type-{name.lower()}", range)
#
#         if not node.returns:
#             node.returns = self.guess_return_type(node, ctx)
#             range = self.get_range(node)
#             self.imports.add_import("Any", "typing")
#             self.changes.add_change("missing-return-type-any", range)
#
#     def get_range(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
#         lineno = node.lineno
#         end_lineno = node.end_lineno or node.lineno
#         if node.body:
#             end_lineno = node.body[0].lineno
#         return (lineno, end_lineno)
#
#     def guess_return_type(
#         self,
#         node: ast.FunctionDef | ast.AsyncFunctionDef,
#         ctx: AST,
#     ) -> ast.expr:
#         returns = self.get_returns(node)
#         if returns is self.UNKNOWN_RETURN:
#             return ast.Name(id=NAME_ANY, ctx=node)
#         elif len(returns) == 0:
#             return ast.Name(id=NAME_NONE, ctx=node)
#         elif (  # if only 1 return and it's a call to a class, we can assume it as the type
#             len(returns) == 1
#             and isinstance(returns[0], ast.Return)
#             and isinstance(returns[0].value, ast.Call)
#             and isinstance(returns[0].value.func, ast.Name)
#             and returns[0].value.func.id[0].isupper()
#             and "_" not in returns[0].value.func.id
#         ):
#             name = returns[0].value.func.id
#             if isinstance(ctx, ast.ClassDef) and ctx.name == name:
#                 return ast.Constant(value=name)
#             else:
#                 return ast.Name(id=name, ctx=node)
#         elif len(returns) == 1:
#             # print(self.opts.filename)
#             # print(returns[0].value.__dict__)
#             return ast.Name(id=NAME_ANY, ctx=node)
#         else:
#             return ast.Name(id=NAME_ANY, ctx=node)
#
#     def get_returns(
#         self,
#         node: ast.FunctionDef | ast.AsyncFunctionDef,
#     ) -> list[ast.Return | ast.Yield | ast.YieldFrom]:
#         try:
#             visitor = ReturnVisitor()
#             visitor.visit(node)
#             return visitor.returns
#         except RecursionError:
#             return self.UNKNOWN_RETURN
#
#
# class ReturnVisitor(ast.NodeVisitor):
#     returns: list[ast.Return | ast.Yield | ast.YieldFrom] = []
#
#     def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
#         self.returns.append(node)
#
#     def visit_Yield(self, node: ast.Yield) -> None:  # noqa: N802
#         self.returns.append(node)
#
#     def visit_YieldFrom(self, node: ast.YieldFrom) -> None:  # noqa: N802
#         self.returns.append(node)
