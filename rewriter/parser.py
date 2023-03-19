import re
from ast import Module, parse, unparse
from difflib import Differ

from black import format_str
from black.mode import Mode, TargetVersion

from rewriter.fixers import FixerStats
from rewriter.options import Options


def parse_tree(opts: Options) -> Module:
    with open(opts.filename) as f:
        opts.source = f.read()
    return parse(opts.source, opts.filename)


def unparse_tree(opts: Options, tree: Module, stats: FixerStats) -> str:
    if not stats:
        return opts.source

    result = unparse(tree)
    reformatted = reformat(result)
    final = merge_new_code(opts, reformatted, stats)

    if not opts.dry_run:
        with open(opts.filename, "w") as f:
            f.write(final)
    return final


def merge_new_code(opts: Options, result: str, stats: FixerStats) -> str:
    result_lines = result.strip().splitlines()
    original = opts.source.splitlines()

    lineno = 0
    final: list[str] = []
    ranges = get_ranges(stats)
    differ = Differ()
    for diff in differ.compare(original, result_lines):
        diff_type = diff[0]
        line = diff[2:]

        if diff_type in (" ", "-"):
            lineno += 1
        in_range = lineno in ranges

        if diff_type == " ":
            final.append(f"{line}\n")

        elif diff_type == "-" and not in_range:
            final.append(f"{line}\n")

        elif diff_type == "+" and in_range:
            final.append(f"{line}\n")

        if opts.verbose:
            indicator = "*" if in_range else " "
            print(f"{lineno} {indicator}: {diff_type} {line}")

    final = add_any_import(final)

    return "".join(final)


def add_any_import(lines: list[str]) -> list[str]:
    # TODO: This is "good enough" to add the Any import, but this should be revisited

    any_check = re.compile("from typing import .*Any")
    imports_start = 0
    for idx, line in enumerate(lines):
        if line.startswith("from") or line.startswith("import"):
            imports_start = idx
        if any_check.match(line):
            return lines

    lines.insert(imports_start, "from typing import Any\n")
    return lines


def get_ranges(stats: FixerStats) -> set[int]:
    ranges: set[int] = set()
    for stat in stats:
        start, end = stat.range
        for i in range(start, end):
            ranges.add(i)
        else:
            ranges.add(start)
    return ranges


def is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def reformat(code: str) -> str:
    black_mode = Mode(target_versions={TargetVersion.PY37}, line_length=100)
    return format_str(code, mode=black_mode)
