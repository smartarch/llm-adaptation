from typing import Any, Union
import abc


class ASTNode(abc.ABC):
    """Base AST node."""
    @abc.abstractmethod
    def evaluate(self, step: int, context: dict[str, Any]) -> bool:
        raise NotImplementedError


class PyExpr(ASTNode):
    def __init__(self, code: str):
        self.code = code
    def __repr__(self):
        return f"PyExpr({self.code!r})"
    def evaluate(self, step: int, context: dict[str, Any]) -> bool | Any:
        return eval(self.code, {}, context)


class TemporalWithin(ASTNode):
    def __init__(self, min_occurrences: Union[int, PyExpr], window: Union[int, PyExpr], expr: ASTNode):
        self.min_occurrences = min_occurrences
        self.window = window
        self.expr = expr
    def __repr__(self):
        return f"Within(min_occurrences={self.min_occurrences!r}, window={self.window!r}, expr={self.expr!r})"
    def evaluate(self, *args) -> bool:
        # TODO: implement proper temporal evaluation
        # Simplified evaluation: just evaluate the expr once per step
        return bool(self.expr.evaluate(*args))


class And(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right
    def __repr__(self):
        return f"And({self.left!r}, {self.right!r})"
    def evaluate(self, *args) -> bool:
        return self.left.evaluate(*args) and self.right.evaluate(*args)


class Or(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right
    def __repr__(self):
        return f"Or({self.left!r}, {self.right!r})"
    def evaluate(self, *args) -> bool:
        return self.left.evaluate(*args) or self.right.evaluate(*args)


class Not(ASTNode):
    def __init__(self, expr: ASTNode):
        self.expr = expr
    def __repr__(self):
        return f"Not({self.expr!r})"
    def evaluate(self, *args) -> bool:
        return not self.expr.evaluate(*args)


class Implies(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right
    def __repr__(self):
        return f"Implies({self.left!r}, {self.right!r})"
    def evaluate(self, *args) -> bool:
        return not self.left.evaluate(*args) or self.right.evaluate(*args)


class ForAll(ASTNode):
    def __init__(self, var: str, set_expr: PyExpr, body: ASTNode):
        self.var = var
        self.set_expr = set_expr
        self.body = body
    def __repr__(self):
        return f"ForAll({self.var!r}, {self.set_expr!r}, {self.body!r})"
    def evaluate(self, step: int, context: dict[str, Any]) -> bool:
        elems: list = self.set_expr.evaluate(step, context) or []  # type: ignore
        ok = True
        for e in elems:
            context[self.var] = e
            if not self.body.evaluate(step, context):
                ok = False
        return ok
