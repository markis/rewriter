import ast
from collections import defaultdict
from operator import attrgetter

from rewriter.trackers.stats import ChangeTracker

Import = ast.Import | ast.ImportFrom
NewImport = tuple[str | None, str]


class ImportTracker:
    change_tracker: ChangeTracker
    tree: ast.Module
    current_imports: list[Import] | None = None
    requested_imports: dict[str, set[str]] = defaultdict(set)

    def __init__(self, change_tracker: ChangeTracker) -> None:
        self.change_tracker = change_tracker

    def add_import(self, name: str, module: str | None = None) -> None:
        self.requested_imports[module or ""].add(name)

    def track_current_imports(self, tree: ast.Module) -> None:
        self.tree = tree
        self.current_imports = [
            node for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)
        ]
        self.current_imports.sort(key=attrgetter("lineno"))

    def write_new_imports(self) -> None:
        if self.current_imports is None:
            raise ValueError("current_imports was never populated")

        for node in self.current_imports:
            if isinstance(node, ast.ImportFrom) and node.module in self.requested_imports:
                node.names.extend(
                    [ast.alias(name=name) for name in self.requested_imports[node.module]]
                )
                node.names.sort(key=lambda node: node.name)
                self.change_tracker.add_change(
                    "update-import", (node.lineno, node.end_lineno or node.lineno), node, node
                )
                del self.requested_imports[node.module]

        first_import = self.current_imports[0]
        idx = self.tree.body.index(first_import) + 1
        end_lineno = first_import.end_lineno or first_import.lineno
        ranges = (end_lineno, end_lineno)
        for module, names in self.requested_imports.items():
            new_import = ast.ImportFrom(module, [ast.alias(name=name) for name in names])
            self.tree.body.insert(idx, new_import)
            self.change_tracker.add_change("update-import", ranges, new_import, new_import)
