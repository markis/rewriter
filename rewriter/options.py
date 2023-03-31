from collections.abc import Iterable
from typing import Protocol


class Options(Protocol):
    filenames: Iterable[str]
    filename: str
    source: str
    dry_run: bool
    verbose: bool
