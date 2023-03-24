from ast import Module, parse, unparse
from difflib import Differ

from black import format_str
from black.mode import Mode, TargetVersion

from rewriter.options import Options
from rewriter.trackers.imports import ImportTracker
from rewriter.trackers.stats import ChangeTracker


def parse_tree(opts: Options) -> Module:
    with open(opts.filename) as f:
        opts.source = f.read()
    return parse(opts.source, opts.filename)


def unparse_tree(
    opts: Options, tree: Module, change_tracker: ChangeTracker, import_tracker: ImportTracker
) -> str:
    if not change_tracker.has_changes or opts.dry_run:
        return opts.source

    try:
        import_tracker.write_new_imports()
        result = unparse(tree)
        reformatted = reformat(result)
        final = merge_new_code(opts, reformatted, change_tracker)
        if not opts.dry_run:
            with open(opts.filename, "w") as f:
                f.write(final)
        return final
    except (TypeError, AttributeError) as e:
        print(f"{opts.filename} failed to unparse")
        print(e)
        return opts.source


def merge_new_code(opts: Options, result: str, change_tracker: ChangeTracker) -> str:
    result_lines = result.strip().splitlines()
    original = opts.source.splitlines()
    ranges = change_tracker.get_change_ranges()

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
