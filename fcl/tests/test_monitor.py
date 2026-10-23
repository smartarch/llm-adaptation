"""Tests of the online monitor on hand-made traces (current semantics)."""
import pytest

from fcl.tests.helpers import run_trace, trace


def test_always_satisfied():
    assert run_trace("always(`p`)", trace(p=[True, True, True])) == []


def test_always_violated_when_predicate_fails():
    violations = run_trace("always(`p`)", trace(p=[True, False, True]))
    assert len(violations) == 1
    assert violations[0].step == 2


def test_once_satisfied():
    assert run_trace("once(`p`)", trace(p=[False, False, True])) == []


def test_once_violated_at_the_end():
    violations = run_trace("once(`p`)", trace(p=[False, False, False]))
    assert len(violations) == 1


def test_within_window():
    assert run_trace("within(1, 2, `p`)", trace(p=[False, True, False, False])) == []
    assert len(run_trace("within(1, 2, `p`)", trace(p=[False, False, True, False]))) == 1


def test_scattered_counts_occurrences():
    assert run_trace("scattered(2, `p`)", trace(p=[True, False, True, False])) == []
    assert len(run_trace("scattered(3, `p`)", trace(p=[True, False, True, False]))) == 1


def test_number_from_python_expression():
    assert run_trace("within(`0.5 * MAX`, MAX, `p`)", trace(p=[True, True, False, False])) == []
    assert len(run_trace("within(`0.5 * MAX`, MAX, `p`)", trace(p=[True, False, False, False]))) == 1


def test_forall_reports_bindings():
    states = trace(xs=[[1, 2], [1, 2], [1, 2]], bad=[set(), {2}, set()])
    violations = run_trace("forall x in `xs`: always(`x not in bad`)", states)
    assert len(violations) == 1
    assert violations[0].bindings == {"x": 2}
    assert violations[0].step == 2


def test_violation_state_contains_context():
    violations = run_trace("always(`p`)", trace(p=[True, False], info=["a", "b"]))
    assert violations[0].state["info"] == "b"


def test_implication_with_past_antecedent():
    # if `a` held in each of the last 2 steps (including the current one), `b` must hold
    formula = "consequent(2, `a`) implies `b`"
    assert run_trace(formula, trace(a=[True, True, True], b=[False, True, True])) == []
    assert len(run_trace(formula, trace(a=[True, True, True], b=[True, False, True]))) == 1


# --- Known bugs of the current implementation (to be fixed in Phase 2) ---

@pytest.mark.xfail(strict=True, reason="Bug 1: the obligation of the consequent is created even if the antecedent is false")
def test_bug_obligation_created_before_trigger():
    # attack before moving to the cave must not satisfy "attack after moving"
    states = trace(moved=[False, False, True, False, False], attacked=[True, False, False, False, False])
    assert len(run_trace("consequent(1, `moved`) implies once(`attacked`)", states)) == 1


@pytest.mark.xfail(strict=True, reason="Bug 2: violation is lost when the antecedent is false at the step the obligation fails")
def test_bug_violation_lost():
    states = trace(moved=[False, True, False, False, False], attacked=[False, False, False, False, False])
    assert len(run_trace("consequent(1, `moved`) implies once(`attacked`)", states)) == 1


@pytest.mark.xfail(strict=True, reason="Bug 3: temporal windows are not strict (the creation state is counted)")
def test_bug_window_not_strict():
    assert len(run_trace("once(`p`)", trace(p=[True, False, False]))) == 1
