import pytest
from lark.exceptions import LarkError

import fcl
from fcl.ast import Always, ForAll, Implies, Pred, Within


def test_pred():
    formula = fcl.parse("`x > 1`")
    assert isinstance(formula, Pred)
    assert formula.code == "x > 1"


def test_escaped_backtick():
    formula = fcl.parse(r"`'\`'`")
    assert isinstance(formula, Pred)
    assert formula.code == "'`'"


@pytest.mark.parametrize("text, n, t", [
    ("within(2, 5, `p`)", 2, 5),
    ("within(1, -3, `p`)", 1, -3),
    ("within(MAX, MAX, `p`)", "MAX", "MAX"),
    ("within(1, BEG, `p`)", 1, "BEG"),
])
def test_within(text, n, t):
    formula = fcl.parse(text)
    assert isinstance(formula, Within)
    assert formula.n == n
    assert formula.t == t
    assert formula.pred.code == "p"


def test_python_expression_as_number():
    formula = fcl.parse("within(`0.8 * MAX`, MAX, `p`)")
    assert isinstance(formula.n, Pred)
    assert formula.n.code == "0.8 * MAX"


def test_always():
    formula = fcl.parse("always(forall x in `xs`: `x > 0` implies within(1, 3, `x > 1`))")
    assert isinstance(formula, Always)
    assert isinstance(formula.body, ForAll)
    assert isinstance(formula.body.body, Implies)


def test_implication_with_past_antecedent():
    formula = fcl.parse("within(2, -2, `a`) implies `b`")
    assert isinstance(formula, Implies)
    assert isinstance(formula.left, Within)
    assert isinstance(formula.right, Pred)


def test_nested_forall():
    formula = fcl.parse("forall x in `xs`: forall y in `ys`: `x != y`")
    assert isinstance(formula, ForAll)
    assert isinstance(formula.body, ForAll)


def test_str_round_trip():
    text = "always(forall x in `xs`: within(1, -2, `a`) implies within(`0.5 * MAX`, MAX, `x in b`))"
    assert str(fcl.parse(text)) == text
    assert str(fcl.parse(str(fcl.parse(text)))) == text


@pytest.mark.parametrize("text", [
    "always(p)",  # predicate must be in backticks
    "once(`p`)",  # removed syntactic sugar
    "scattered(2, `p`)",
    "consequent(2, `p`)",
    "next(`p`)",
    "within(1, 2, always(`p`))",  # only a predicate inside within
])
def test_syntax_errors(text):
    with pytest.raises(LarkError):
        fcl.parse(text)


@pytest.mark.parametrize("text", [
    "within(1, 2, `a`) implies `b`",  # future within in antecedent
    "`a` implies within(1, -2, `b`)",  # past within in consequent
    "always(always(`p`))",  # nested always
    "always(forall x in `xs`: always(`p`))",
])
def test_unsupported_formulas(text):
    with pytest.raises(fcl.FCLError):
        fcl.parse(text)
