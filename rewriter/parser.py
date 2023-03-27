from ast import Module, parse, unparse
from collections.abc import Sequence
from difflib import Differ

from black import format_str
from black.mode import Mode, TargetVersion

from rewriter.options import Options
from rewriter.trackers.changes import Change, get_change_ranges
from rewriter.trackers.imports import Import, update_tree


def parse_tree(opts: Options) -> Module:
    with open(opts.filename) as f:
        opts.source = f.read()
    return parse(opts.source, opts.filename)


def unparse_tree(
    opts: Options, tree: Module, changes: Sequence[Change], imports: Sequence[Import]
) -> str:
    if not changes:
        return opts.source

    try:
        updated_changes = list(changes)
        updated_changes += update_tree(tree, imports)
        result = unparse(tree)
        reformatted = reformat(result)
        final = merge_new_code(opts, reformatted, updated_changes)
        if not opts.dry_run:
            with open(opts.filename, "w") as f:
                f.write(final)
        return final
    except (TypeError, AttributeError) as e:
        print(f"{opts.filename} failed to unparse")
        print(e)
        return opts.source


def merge_new_code(opts: Options, result: str, changes: Sequence[Change]) -> str:
    result_lines = result.strip().splitlines()
    original = opts.source.splitlines()
    ranges = get_change_ranges(changes)

    lineno = 0
    final: list[str] = []
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
            diff_type = "*" if diff_type == "+" and in_range else diff_type
            print(f"{lineno}: {diff_type} {line}")

    if opts.verbose:
        print(f"Replacement lines: {sorted(list(ranges))}")

    return "".join(final)


def reformat(code: str) -> str:
    black_mode = Mode(target_versions={TargetVersion.PY37}, line_length=100)
    return format_str(code, mode=black_mode)
