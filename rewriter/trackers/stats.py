import ast
from dataclasses import dataclass
from typing import overload

Range = tuple[int, int]
EMPTY_AST: ast.AST = ast.AST()


@dataclass(frozen=True)
class Change:
    range: Range
    type: str
    fixed: ast.AST
    node: ast.AST


class ChangeTracker:
    changes: list[Change] = []

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)

    @overload
    def add_change(self, change: Change) -> None:
        ...

    @overload
    def add_change(self, change: str, range: Range, fixed: ast.AST, node: ast.AST) -> None:
        ...

    def add_change(
        self,
        change: str | Change,
        range: Range = (0, 0),
        fixed: ast.AST = EMPTY_AST,
        node: ast.AST = EMPTY_AST,
    ) -> None:
        if isinstance(change, str):
            self.changes.append(Change(range, change, fixed, node))
        else:
            self.changes.append(change)

    def get_change_ranges(self) -> set[int]:
        ranges: set[int] = set()
        for stat in self.changes:
            start, end = stat.range
            for i in range(start, end):
                ranges.add(i)
            else:
                ranges.add(start)
        return ranges
