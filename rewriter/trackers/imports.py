import ast
from collections import defaultdict
from operator import attrgetter

from rewriter.trackers.changes import ChangeTracker

Import = ast.Import | ast.ImportFrom
NewImport = tuple[str | None, str]


class ImportTracker:
    requested: dict[str, set[str]] = defaultdict(set)

    def add_import(self, name: str, module: str | None = None) -> None:
        self.requested[module or ""].add(name)

    def update_tree(self, tree: ast.Module, changes: ChangeTracker) -> None:
        current = [node for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)]
        current.sort(key=attrgetter("lineno"))

        for node in current:
            if isinstance(node, ast.ImportFrom) and node.module in self.requested:
                node.names.extend([ast.alias(name=name) for name in self.requested[node.module]])
                node.names.sort(key=attrgetter("name"))
                changes.add_change("update-import", (node.lineno, node.end_lineno or node.lineno))
                del self.requested[node.module]

        first_import = current[0]
        idx = tree.body.index(first_import) + 1
        end_lineno = first_import.end_lineno or first_import.lineno
        ranges = (end_lineno, end_lineno)
        for module, names in self.requested.items():
            new_import = ast.ImportFrom(module, [ast.alias(name=name) for name in names])
            tree.body.insert(idx, new_import)
            changes.add_change("update-import", ranges)
