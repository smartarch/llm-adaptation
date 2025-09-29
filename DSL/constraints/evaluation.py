from collections import defaultdict
from typing import Any, Union
import abc

from utils import HashableDict


def resolve_number(expr: Union[int, "PyExpr"], step: int, context: dict[str, Any], bindings: dict[str, Any]) -> int:
    if isinstance(expr, int):
        return expr
    else:
        return int(expr.evaluate(step, context, bindings))


class ASTNode(abc.ABC):
    """Base AST node."""
    @abc.abstractmethod
    def evaluate(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool | list["TemporalObligation"]:
        raise NotImplementedError


class PyExpr(ASTNode):
    def __init__(self, code: str):
        self.code = code

    def __repr__(self):
        return f"PyExpr({self.code!r})"

    def evaluate(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool | Any:
        return eval(self.code, context | bindings)


class TemporalWithin(ASTNode):
    """Temporal operator evaluated via future obligation."""
    def __init__(self, min_occurrences: Union[int, PyExpr], window: Union[int, PyExpr], expr: PyExpr):
        self.min_occurrences = min_occurrences
        self.window = window
        self.expr = expr
        self.obligations: dict[HashableDict, TemporalObligation] = {}

    def __repr__(self):
        return f"Within(min_occurrences={self.min_occurrences!r}, window={self.window!r}, expr={self.expr!r})"

    def evaluate(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool | list["TemporalObligation"]:
        bound_variables = HashableDict(bindings)
        if bound_variables in self.obligations:
            return self.obligations[bound_variables].evaluate(step, context, bindings)

        obligation = TemporalObligation(
            resolve_number(self.min_occurrences, step, context, bindings),
            resolve_number(self.window, step, context, bindings),
            self.expr,
            step,
            bound_variables,
        )
        self.obligations[bound_variables] = obligation
        return [obligation]


class TemporalObligation(ASTNode):
    def __init__(self, min_occurrences: int, window: int, expr: PyExpr, step: int, bound_variables: HashableDict):
        self.min_occurrences = min_occurrences
        self.window = window
        self.expr = expr
        self.start_step = step
        self.end_step = step + window
        self.occurences = 0
        self.resolved = False
        self.bound_variables = bound_variables

    def evaluate(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool | list["TemporalObligation"]:
        if self.resolved:
            return True

        current = bool(self.expr.evaluate(step, context, bindings))
        if current:
            self.occurences += 1

        # end of obligation window reached
        if step >= self.end_step:
            self.resolved = True
            return self.occurences >= self.min_occurrences

        # not enough remaining steps to satisfy obligation
        remaining_steps = self.end_step - step
        if self.min_occurrences - self.occurences > remaining_steps:
            self.resolved = True
            return False

        # not yet resolved
        return [self]


class TemporalHistory(ASTNode):
    """Temporal operator evaluated via history (used within antecedent of implies)."""
    def __init__(self, min_occurrences: Union[int, PyExpr], window: Union[int, PyExpr], expr: PyExpr):
        self.min_occurrences = min_occurrences
        self.window = window
        self.expr = expr
        self.history: dict[HashableDict, list[bool]] = defaultdict(list)

    def __repr__(self):
        return f"TemporalHistory(min_occurrences={self.min_occurrences!r}, window={self.window!r}, expr={self.expr!r})"

    def evaluate(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool:
        result = bool(self.expr.evaluate(step, context, bindings))
        bound_variables = HashableDict(bindings)
        self.history[bound_variables].append(result)
        return self.check(step, context, bound_variables)

    def check(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool:
        window = resolve_number(self.window, step, context, bindings)
        min_occurences = resolve_number(self.min_occurrences, step, context, bindings)
        bound_variables = HashableDict(bindings)
        history = self.history[bound_variables][-window:]
        occurrences = sum(1 for r in history if r)
        return occurrences >= min_occurences


class Implies(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Implies({self.left!r}, {self.right!r})"
    
    def evaluate(self, *args) -> bool | list["TemporalObligation"]:
        right_eval = self.right.evaluate(*args)  # we need to evaluate right side anyway to evaluate existing obligations
        if self.left.evaluate(*args):
            return right_eval
        return True


class ForAll(ASTNode):
    def __init__(self, var: str, set_expr: PyExpr, body: ASTNode):
        self.var = var
        self.set_expr = set_expr
        self.body = body
        self.violations: list[dict[str, Any]] = []

    def __repr__(self):
        return f"ForAll({self.var!r}, {self.set_expr!r}, {self.body!r})"

    def evaluate(self, step: int, context: dict[str, Any], bindings: dict[str, Any]) -> bool | list["TemporalObligation"]:
        elems: list = self.set_expr.evaluate(step, context, bindings) or []  # type: ignore[assignment]
        obligations = []
        self.violations = []
        for e in elems:
            bindings = bindings.copy() | {self.var: e}
            eval_result = self.body.evaluate(step, context, bindings)
            if isinstance(eval_result, list):
                obligations.extend(eval_result)
            else:
                if eval_result is False:
                    self.violations.append(bindings)
        if obligations:
            return obligations
        return not self.violations
