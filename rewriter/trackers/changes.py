from collections.abc import Sequence
from dataclasses import dataclass

Range = tuple[int, int]


@dataclass(frozen=True)
class Change:
    range: Range
    type: str


def get_change_ranges(changes: Sequence[Change]) -> set[int]:
    ranges: set[int] = set()
    for stat in changes:
        start, end = stat.range
        for i in range(start, end):
            ranges.add(i)
        else:
            ranges.add(start)
    return ranges
