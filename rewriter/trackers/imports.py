import ast
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from operator import attrgetter

from rewriter.trackers.changes import Change

ImportType = ast.Import | ast.ImportFrom


@dataclass
class Import:
    module: str
    name: str


def update_tree(tree: ast.Module, imports: Iterable[Import]) -> Iterable[Change]:
    changes: list[Change] = []
    current = [node for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)]
    current.sort(key=attrgetter("lineno"))

    requested: dict[str, set[str]] = defaultdict(set)
    for i in imports:
        requested[i.module or ""].add(i.name)

    for node in current:
        if isinstance(node, ast.ImportFrom) and node.module in requested:
            node.names.extend([ast.alias(name=name) for name in requested[node.module]])
            node.names.sort(key=attrgetter("name"))
            changes.append(Change((node.lineno, node.end_lineno or node.lineno), "update-import"))
            del requested[node.module]

    first_import = current[0] if len(current) > 0 else None
    if first_import:
        idx = tree.body.index(first_import) + 1
        end_lineno = first_import.end_lineno or first_import.lineno
        ranges = (end_lineno, end_lineno)
    else:
        idx = 0
        ranges = (1, 1)

    for module, names in requested.items():
        new_import = ast.ImportFrom(module, [ast.alias(name=name) for name in names])
        tree.body.insert(idx, new_import)
        changes.append(Change(ranges, "update-import"))

    return changes
