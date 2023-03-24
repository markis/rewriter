import ast
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Mapping, Sequence

from rewriter.options import Options
from rewriter.trackers.imports import ImportTracker
from rewriter.trackers.stats import ChangeTracker

ASTType = type[ast.AST]
FixTypes = Sequence[ASTType]
FixerMap = Mapping[ASTType, Sequence["Fixer"]]


NAME_ANY = "Any"
NAME_BOOL = "bool"
NAME_INT = "int"
NAME_NONE = "None"
NAME_STR = "str"
NAME_CLS = "cls"
NAME_SELF = "self"
NAME_TYPING = "typing"


class Fixer(ABC):
    opts: Options
    import_tracker: ImportTracker
    change_tracker: ChangeTracker

    def __init__(
        self, opts: Options, stats_tracker: ChangeTracker, import_tracker: ImportTracker
    ) -> None:
        self.opts = opts
        self.import_tracker = import_tracker
        self.change_tracker = stats_tracker

    @classmethod
    def get_fixers(
        cls, opts: Options, stats_tracker: ChangeTracker, import_tracker: ImportTracker
    ) -> FixerMap:
        fixers = defaultdict(list)
        for fixer in cls.__subclasses__():
            for fixer_type in fixer.get_fix_types():
                fixers[fixer_type].append(fixer(opts, stats_tracker, import_tracker))
        return fixers

    @classmethod
    @abstractmethod
    def get_fix_types(cls) -> FixTypes:
        raise NotImplementedError()

    @abstractmethod
    def fix(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> None:
        raise NotImplementedError()


class ArgumentFixer(Fixer):
    @classmethod
    def get_fix_types(cls) -> FixTypes:
        return [ast.arguments]

    def fix(self, node: ast.AST, parent: ast.AST, ctx: ast.AST) -> None:
        if isinstance(node, ast.arguments):
            self.fix_args(node, parent, ctx)

    def fix_args(self, node: ast.arguments, parent: ast.AST, ctx: ast.AST) -> None:
        if node.vararg:
            self.fix_arg(node.vararg, parent, ctx)

        if node.kwarg:
            self.fix_arg(node.kwarg, parent, ctx)

        for arg in node.args:
            self.fix_arg(arg, parent, ctx)

        for arg in node.posonlyargs:
            self.fix_arg(arg, parent, ctx)

        for arg in node.kwonlyargs:
            self.fix_arg(arg, parent, ctx)

    def fix_arg(self, node: ast.arg, parent: ast.AST, ctx: ast.AST) -> None:
        if isinstance(ctx, ast.ClassDef) and node.arg in (NAME_CLS, NAME_SELF):
            return

        if not node.annotation:
            node.annotation = ast.Name(id=NAME_ANY)
            self.import_tracker.add_import("Any", "typing")
            self.change_tracker.add_change("missing-arg-type", self.get_range(node), node, parent)

    def get_range(self, node: ast.arg) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno or node.lineno
        return (lineno, end_lineno)


class ClassFixer(Fixer):
    METHODS_MAP = [
        ("None", {"__init__"}),
        ("bool", {"__lt__", "__le__", "__ne__", "__eq__", "__gt__", "__ge__", "__bool__"}),
        ("int", {"__hash__"}),
        ("Self", {"__new__"}),
        ("str", {"__str__", "__repr__"}),
    ]
    UNKNOWN_RETURN: list[ast.Return | ast.Yield | ast.YieldFrom] = []

    @classmethod
    def get_fix_types(cls) -> FixTypes:
        return [ast.FunctionDef, ast.AsyncFunctionDef]

    def fix(self, node: ast.AST, _: ast.AST, ctx: ast.AST) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            self.fix_func(node, ctx)

    def fix_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, ctx: ast.AST) -> None:
        if isinstance(ctx, ast.ClassDef):
            for name, methods in self.METHODS_MAP:
                if node.name in methods and not node.returns:
                    if name == "Self":
                        node.returns = ast.Name(id=ast.Constant(ctx.name), ctx=node)
                    else:
                        node.returns = ast.Name(id=name, ctx=node)
                    range = self.get_range(node)
                    self.import_tracker.add_import("Any", "typing")
                    self.change_tracker.add_change(
                        f"missing-return-type-{name.lower()}", range, node, node
                    )

        if not node.returns:
            node.returns = self.guess_return_type(node, ctx)
            range = self.get_range(node)
            self.import_tracker.add_import("Any", "typing")
            self.change_tracker.add_change("missing-return-type-any", range, node, node)

    def get_range(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
        lineno = node.lineno
        end_lineno = node.end_lineno or node.lineno
        if node.body:
            end_lineno = node.body[0].lineno
        return (lineno, end_lineno)

    def guess_return_type(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        ctx: ast.AST,
    ) -> ast.expr:
        returns = self.get_returns(node)
        if returns is self.UNKNOWN_RETURN:
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
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[ast.Return | ast.Yield | ast.YieldFrom]:
        try:
            visitor = ReturnVisitor()
            visitor.visit(node)
            return visitor.returns
        except RecursionError:
            return self.UNKNOWN_RETURN


class ReturnVisitor(ast.NodeVisitor):
    returns: list[ast.Return | ast.Yield | ast.YieldFrom] = []

    def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
        self.returns.append(node)

    def visit_Yield(self, node: ast.Yield) -> None:  # noqa: N802
        self.returns.append(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:  # noqa: N802
        self.returns.append(node)
