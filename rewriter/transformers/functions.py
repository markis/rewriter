import ast

from rewriter.trackers.changes import Change
from rewriter.trackers.imports import Import
from rewriter.transformers import TransformerReturnType, transformer

AST = ast.AST

NAME_ANY = "Any"
NAME_BOOL = "bool"
NAME_INT = "int"
NAME_NONE = "None"
NAME_STR = "str"
NAME_TYPING = "typing"

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
                imports.append(Import("typing", "Any"))
                changes.append(Change(_get_range(node), f"missing-return-type-{name.lower()}"))

    if not node.returns:
        node.returns = _guess_return_type(node, ctx)
        imports.append(Import("typing", "Any"))
        changes.append(Change(_get_range(node), "missing-return-type-any"))

    return changes, imports


def _get_range(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
    lineno = node.lineno
    end_lineno = node.end_lineno or node.lineno
    if node.body:
        end_lineno = node.body[0].lineno
    return (lineno, end_lineno)


def _guess_return_type(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    ctx: AST,
) -> ast.expr:
    returns = _get_returns(node)
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


def _get_returns(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Return | ast.Yield | ast.YieldFrom]:
    try:
        visitor = _ReturnVisitor()
        visitor.visit(node)
        return visitor.returns
    except RecursionError:
        return UNKNOWN_RETURN


class _ReturnVisitor(ast.NodeVisitor):
    returns: list[ast.Return | ast.Yield | ast.YieldFrom] = []

    def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
        self.returns.append(node)

    def visit_Yield(self, node: ast.Yield) -> None:  # noqa: N802
        self.returns.append(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:  # noqa: N802
        self.returns.append(node)
