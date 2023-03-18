from ast import Module, parse, unparse
from difflib import Differ

from black import format_str
from black.mode import Mode, TargetVersion

from rewriter.options import Options


def parse_tree(opts: Options) -> Module:
    with open(opts.filename) as f:
        opts.source = f.read()
    return parse(opts.source, opts.filename)


def unparse_tree(opts: Options, tree: Module) -> str:
    result = unparse(tree)
    reformatted = reformat(result)
    final = merge_new_code(opts, reformatted)

    if not opts.dry_run:
        with open(opts.filename, "w") as f:
            f.write(final)
    return final


def merge_new_code(opts: Options, result: str) -> str:
    result_lines = result.strip().splitlines()
    original = opts.source.splitlines()

    final: list[str] = []
    differ = Differ()
    for diff in differ.compare(original, result_lines):
        diff_type = diff[0]
        line = diff[2:]

        if diff_type in (" ", "+"):
            final.append(f"{line}\n")
        elif diff_type == "-" and is_empty_or_comment(line):
            final.append(f"{line}\n")

    return "".join(final)


def is_empty_or_comment(line: str) -> bool:
    return not line or line.lstrip().startswith("#")


def reformat(code: str) -> str:
    black_mode = Mode(target_versions={TargetVersion.PY37}, line_length=100)
    return format_str(code, mode=black_mode)
