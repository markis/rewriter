from typing import Protocol


class Options(Protocol):
    filename: str
    source: str
    dry_run: bool
    verbose: bool
