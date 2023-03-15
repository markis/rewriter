from ast import Module, parse, unparse

from rewriter.options import Options


def parse_tree(opts: Options) -> Module:
    with open(opts.filename) as f:
        source = f.read()
    return parse(source, opts.filename)


def unparse_tree(opts: Options, tree: Module) -> None:
    result = unparse(tree)
    with open(opts.filename, "w") as f:
        f.write(result)
