import pkgutil
from ast import AST
from collections import defaultdict
from collections.abc import Callable, Iterable

from rewriter.trackers.changes import Change
from rewriter.trackers.imports import Import

TransformerReturnType = tuple[Iterable[Change], Iterable[Import]]
Transformer = Callable[[AST, AST, AST], TransformerReturnType]
Transform = Callable[[AST, AST, AST], Iterable[TransformerReturnType]]

__all__ = ["Transform", "TransformerReturnType", "transform", "transformer"]

__registry = defaultdict(list)


def transformer(*types: type[AST]) -> Callable[[Transformer], None]:
    """
    Decorator to register a function as a transformer
    """

    def wrapper(func: Transformer) -> None:
        for t in types:
            __registry[t].append(func)

    return wrapper


def transform(node: AST, parent: AST, ctx: AST) -> Iterable[TransformerReturnType]:
    """
    Transform a node using the transformers in the registry
    """
    return [func(node, parent, ctx) for func in __registry[type(node)]]


def load_transformers(base_dir: str) -> None:
    """
    Automatically load every module in this folder, which will automatically register transformers
    """

    for _, module, __ in pkgutil.iter_modules([f"{base_dir}/transformers/"]):
        del _, __
        __import__(f"rewriter.transformers.{module}")
