from re import Pattern
from types import TracebackType
from typing import (
    Any,
    Generic,
    TypeVar,
)

E = TypeVar("E", bound=BaseException)

class RaisesContext(Generic[E]):
    def __init__(
        self,
        expected_exception: type[E] | tuple[type[E], ...],
        message: str,
        match_expr: str | Pattern[str] | None = None,
    ) -> None: ...
    def __enter__(self) -> Any: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool: ...

def raises(
    expected_exception: type[E] | tuple[type[E], ...],
    *,
    match: str | Pattern[str] | None = ...,
) -> RaisesContext[E]: ...

__all__ = ["raises"]
