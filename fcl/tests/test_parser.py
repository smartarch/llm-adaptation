import pytest
from lark.exceptions import LarkError

import fcl
from fcl.ast import ForAll, Implies, PyExpr, TemporalHistory, TemporalWithin


def test_py_expr():
    formula = fcl.parse("`x > 1`")
    assert isinstance(formula, PyExpr)
    assert formula.code == "x > 1"


def test_escaped_backtick():
    formula = fcl.parse(r"`'\`'`")
    assert isinstance(formula, PyExpr)
    assert formula.code == "'`'"


@pytest.mark.parametrize("text, min_occurrences, window", [
    ("within(2, 5, `p`)", 2, 5),
    ("scattered(3, `p`)", 3, "MAX"),
    ("consequent(4, `p`)", 4, 4),
    ("always(`p`)", "MAX", "MAX"),
    ("once(`p`)", 1, "MAX"),
    ("next(`p`)", 1, 1),
])
def test_temporal_operators(text, min_occurrences, window):
    formula = fcl.parse(text)
    assert isinstance(formula, TemporalWithin)

    def value(arg):
        return arg.code if isinstance(arg, PyExpr) else arg

    assert value(formula.min_occurrences) == min_occurrences
    assert value(formula.window) == window
    assert formula.expr.code == "p"


def test_python_expression_as_number():
    formula = fcl.parse("within(`0.8 * MAX`, MAX, `p`)")
    assert isinstance(formula.min_occurrences, PyExpr)
    assert formula.min_occurrences.code == "0.8 * MAX"


def test_implication_with_temporal_antecedent_uses_history():
    formula = fcl.parse("consequent(1, `a`) implies once(`b`)")
    assert isinstance(formula, Implies)
    assert isinstance(formula.left, TemporalHistory)
    assert isinstance(formula.right, TemporalWithin)


def test_forall():
    formula = fcl.parse("forall x in `xs`: always(`x > 0`)")
    assert isinstance(formula, ForAll)
    assert formula.var == "x"
    assert formula.set_expr.code == "xs"
    assert isinstance(formula.body, TemporalWithin)


def test_forall_with_implication():
    formula = fcl.parse("forall x in `xs`: `x > 0` implies once(`x > 1`)")
    assert isinstance(formula, ForAll)
    assert isinstance(formula.body, Implies)


def test_syntax_error():
    with pytest.raises(LarkError):
        fcl.parse("always(p)")  # predicate must be in backticks
