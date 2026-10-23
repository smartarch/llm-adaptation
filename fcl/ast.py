"""AST of FCL formulas.

The nodes are immutable descriptions of the formula. All evaluation state (obligations, history) is kept in the
`Monitor`, so one parsed formula can be monitored repeatedly (e.g., in several runs).
"""
import dataclasses
from typing import Union


class FCLError(ValueError):
    """Invalid FCL formula (syntax not supported by the implemented subset)."""


class Node:
    """Base AST node."""


@dataclasses.dataclass(eq=False)
class Pred(Node):
    """Python predicate (or expression), evaluated with `eval` in the current state."""
    code: str

    def __str__(self):
        return f"`{self.code}`"


Num = Union[int, str, Pred]
"""Numeric argument of `within`: a literal integer, "MAX", "BEG", or a Python expression."""


def num_to_str(num: Num) -> str:
    return str(num)


@dataclasses.dataclass(eq=False)
class Within(Node):
    """`within(n, t, pred)`: `pred` holds in at least n states of the strict window of length |t|.

    For t > 0, the window are the next t states (future); for t < 0, the previous |t| states (past).
    """
    n: Num
    t: Num
    pred: Pred

    def __str__(self):
        return f"within({num_to_str(self.n)}, {num_to_str(self.t)}, {self.pred})"


@dataclasses.dataclass(eq=False)
class Always(Node):
    """`always(body)`: the body holds in every following state (= within(MAX, MAX, body))."""
    body: Node

    def __str__(self):
        return f"always({self.body})"


@dataclasses.dataclass(eq=False)
class Implies(Node):
    """`left implies right`. Left is a predicate or a past `within`, right is a predicate or a future `within`."""
    left: Node
    right: Node

    def __str__(self):
        return f"{self.left} implies {self.right}"


@dataclasses.dataclass(eq=False)
class ForAll(Node):
    """`forall var in set_expr: body`."""
    var: str
    set_expr: Pred
    body: Node

    def __str__(self):
        return f"forall {self.var} in {self.set_expr}: {self.body}"
