import os
import pkgutil
from ast import AST
from collections import defaultdict
from collections.abc import Callable, MutableSequence

from rewriter.trackers.changes import Change
from rewriter.trackers.imports import Import

TransformerReturnType = tuple[MutableSequence[Change], MutableSequence[Import]]
Transformer = Callable[[AST, AST, AST], TransformerReturnType]
Transform = Callable[[AST, AST, AST], MutableSequence[TransformerReturnType]]

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


def transform(node: AST, parent: AST, ctx: AST) -> MutableSequence[TransformerReturnType]:
    """
    Transform a node using the transformers in the registry
    """
    return [func(node, parent, ctx) for func in __registry[type(node)]]


# automatically load every module in this folder and automatically register transformers
for _, module, __ in pkgutil.iter_modules([os.path.dirname(__file__)]):
    __import__(f"rewriter.transformers.{module}")
