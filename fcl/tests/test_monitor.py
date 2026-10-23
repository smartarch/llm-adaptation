"""Tests of the online monitor on hand-made traces.

In the traces, the first state is the initial state s_0 (where the top-level formula is evaluated),
the following states are s_1, ..., s_k.
"""
import pytest

import fcl
from fcl.tests.helpers import run_trace, steps_of, trace


# --- top-level predicates and windows ---

def test_top_level_predicate_checked_only_in_initial_state():
    assert steps_of(run_trace("`p`", trace(p=[False, True, True]))) == [0]
    assert run_trace("`p`", trace(p=[True, False, False])) == []


def test_future_window_is_strict():
    # the initial state is not part of the window
    assert len(run_trace("within(1, MAX, `p`)", trace(p=[True, False, False]))) == 1
    assert run_trace("within(1, MAX, `p`)", trace(p=[False, False, True])) == []


def test_window_covers_last_state():
    assert run_trace("within(1, MAX, `p`)", trace(p=[False, False, False, True])) == []


def test_bounded_window():
    # window of 2 states after s_0: s_1, s_2
    assert run_trace("within(1, 2, `p`)", trace(p=[False, False, True, False])) == []
    violations = run_trace("within(1, 2, `p`)", trace(p=[False, False, False, True]))
    assert steps_of(violations) == [2]
    assert violations[0].trigger_step == 0
    assert (violations[0].required, violations[0].occurred) == (1, 0)


def test_counting():
    assert run_trace("within(2, MAX, `p`)", trace(p=[False, True, False, True])) == []
    assert len(run_trace("within(3, MAX, `p`)", trace(p=[False, True, False, True]))) == 1


def test_early_violation():
    # 3 occurrences needed in 3 states: violated as soon as one is missing
    assert steps_of(run_trace("within(MAX, MAX, `p`)", trace(p=[True, True, False, True]))) == [2]


def test_early_satisfaction():
    # obligation is resolved as soon as it is satisfied (later states do not matter)
    assert run_trace("within(1, MAX, `p`)", trace(p=[False, True, False, False])) == []


def test_n_rounded_up():
    # ceil(0.5 * 3) = 2
    assert run_trace("within(`0.5 * MAX`, MAX, `p`)", trace(p=[False, True, True, False])) == []
    assert len(run_trace("within(`0.5 * MAX`, MAX, `p`)", trace(p=[False, True, False, False]))) == 1


def test_n_zero_and_t_zero():
    assert run_trace("within(0, MAX, `p`)", trace(p=[False, False])) == []
    assert run_trace("within(0, 0, `p`)", trace(p=[False, False])) == []
    assert steps_of(run_trace("within(1, 0, `p`)", trace(p=[True, True]))) == [0]


def test_window_too_short_violated_immediately():
    # 3 occurrences required, but only 2 states remain
    violations = run_trace("within(3, 5, `p`)", trace(p=[True, True, True]))
    assert steps_of(violations) == [0]


# --- always ---

def test_always():
    assert run_trace("always(`p`)", trace(p=[False, True, True])) == []  # initial state not checked
    assert steps_of(run_trace("always(`p`)", trace(p=[True, False, True, False]))) == [1, 3]


def test_always_creates_obligation_in_each_state():
    # every state with `a` requires `b` in one of the next 2 states
    formula = "always(`a` implies within(1, 2, `b`))"
    assert run_trace(formula, trace(a=[False, True, False, True, False, False], b=[False, False, True, False, True, False])) == []
    violations = run_trace(formula, trace(a=[False, True, True, False, False, False], b=[False, False, True, False, False, False]))
    # trigger in s_1 is satisfied by s_2; trigger in s_2 (repeated trigger!) needs `b` in s_3 or s_4
    assert steps_of(violations) == [4]
    assert violations[0].trigger_step == 2


def test_implication_obligation_created_only_when_antecedent_holds():
    # attack before moving to the cave does not satisfy "attack after moving" (bug 1 of the original implementation)
    formula = "always(`moved` implies within(1, MAX, `attacked`))"
    states = trace(moved=[False, False, False, True, False, False], attacked=[False, True, False, False, False, False])
    assert steps_of(run_trace(formula, states)) == [5]


def test_violation_not_lost_when_antecedent_false():
    # bug 2 of the original implementation
    formula = "always(`moved` implies within(1, MAX, `attacked`))"
    states = trace(moved=[False, True, False, False, False], attacked=[False, False, False, False, False])
    assert steps_of(run_trace(formula, states)) == [4]


def test_obligation_at_last_state_needs_guard():
    formula = "always(`a` implies within(1, MAX, `b`))"
    # trigger in the last state: empty window -> violation
    assert steps_of(run_trace(formula, trace(a=[False, False, True], b=[False, False, False]))) == [2]
    guarded = "always(`a and MAX > 0` implies within(1, MAX, `b`))"
    assert run_trace(guarded, trace(a=[False, False, True], b=[False, False, False])) == []


def test_consequent_predicate():
    formula = "always(`a` implies `b`)"
    assert steps_of(run_trace(formula, trace(a=[True, True, False, True], b=[False, False, False, True]))) == [1]


# --- past windows ---

def test_past_window_is_strict_and_truncated():
    # "if `gap` held in the 2 previous states, it must not hold now" (= no 3 consecutive gaps)
    formula = "always(within(2, -2, `gap`) implies `not gap`)"
    assert run_trace(formula, trace(gap=[False, True, True, False, True, True])) == []
    assert steps_of(run_trace(formula, trace(gap=[False, True, True, True, False, False]))) == [3]


def test_past_window_starts_with_first_evaluation():
    # the body of `always` is first evaluated in s_1, so the history starts there (truncated window)
    formula = "always(within(1, -3, `p`) implies `q`)"
    assert run_trace(formula, trace(p=[True, False, False, False], q=[False, False, False, False])) == []
    assert steps_of(run_trace(formula, trace(p=[False, True, False, False, False], q=[False, False, True, True, False]))) == [4]


def test_past_window_with_beg():
    # within(1, -BEG, p): p held at least once in all previous states
    formula = "always(within(1, `-BEG`, `p`) implies `q`)"
    assert steps_of(run_trace(formula, trace(p=[False, True, False, False], q=[False, False, False, True]))) == [2]


def test_past_window_per_binding():
    formula = "always(forall x in `xs`: within(1, -1, `x in marked`) implies `x in done`)"
    states = trace(xs=[[1, 2]] * 4, marked=[set(), {1}, {2}, set()], done=[set(), set(), {1}, set()])
    violations = run_trace(formula, states)
    assert [(v.step, v.bindings["x"]) for v in violations] == [(3, 2)]


# --- forall ---

def test_top_level_forall_ranges_over_initial_elements():
    formula = "forall x in `xs`: always(`x not in bad`)"
    states = trace(xs=[[1], [1, 2], [1, 2]], bad=[set(), {2}, {1}])
    violations = run_trace(formula, states)
    assert [(v.step, v.bindings) for v in violations] == [(2, {"x": 1})]


def test_forall_inside_always_covers_new_elements():
    formula = "always(forall x in `xs`: `x not in bad`)"
    states = trace(xs=[[1], [1, 2], [1, 2]], bad=[set(), {2}, {1}])
    violations = run_trace(formula, states)
    assert [(v.step, v.bindings) for v in violations] == [(1, {"x": 2}), (2, {"x": 1})]


def test_nested_forall():
    formula = "always(forall x in `xs`: forall y in `xs`: `x == y or (x, y) not in conflicts`)"
    states = trace(xs=[[1, 2]] * 2, conflicts=[set(), {(1, 2)}])
    violations = run_trace(formula, states)
    assert [v.bindings for v in violations] == [{"x": 1, "y": 2}]


def test_violation_contains_state():
    violations = run_trace("always(`p`)", trace(p=[True, True, False], info=["a", "b", "c"]))
    assert violations[0].state["info"] == "c"
    assert violations[0].state["MAX"] == 0
    assert violations[0].state["BEG"] == 2


def test_violation_contains_trigger_state():
    formula = "always(`a` implies within(1, 1, `b`))"
    violations = run_trace(formula, trace(a=[False, True, False], b=[False, False, False], info=["x", "y", "z"]))
    assert violations[0].trigger_state["info"] == "y"
    assert violations[0].state["info"] == "z"


# --- removed objects ---

class Obj:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def test_existing_objects_drop_obligations():
    a, b = Obj("a"), Obj("b")
    formula = fcl.parse("always(forall x in `xs`: `x in sent` implies within(1, MAX, `x in done`))")
    monitor = fcl.Monitor(formula, 3)
    monitor.start({"xs": [a, b], "sent": set(), "done": set()})
    assert monitor.step({"xs": [a, b], "sent": {a, b}, "done": set()}, existing_objects=[a, b]) == []
    # b is removed from the system before completing its obligation
    assert monitor.step({"xs": [a], "sent": set(), "done": set()}, existing_objects=[a]) == []
    violations = monitor.step({"xs": [a], "sent": set(), "done": set()}, existing_objects=[a])
    assert [v.bindings["x"] for v in violations] == [a]
    assert monitor.finish() == []


# --- end of the trace ---

def test_premature_end_drops_pending_obligations():
    states = trace(p=[False, False, False, False, False])
    assert len(run_trace("within(1, MAX, `p`)", states)) == 1
    assert run_trace("within(1, MAX, `p`)", states, finish_after=2) == []


def test_violations_found_before_premature_end_are_reported():
    states = trace(p=[True, False, True, True, True])
    assert steps_of(run_trace("always(`p`)", states, finish_after=2)) == [1]


def test_monitor_lifecycle_errors():
    monitor = fcl.Monitor(fcl.parse("`p`"), 1)
    with pytest.raises(RuntimeError):
        monitor.step({"p": True})
    monitor.start({"p": True})
    monitor.step({"p": True})
    with pytest.raises(RuntimeError):
        monitor.step({"p": True})
    assert monitor.is_complete


def test_formula_can_be_monitored_repeatedly():
    formula = fcl.parse("within(1, MAX, `p`)")
    for _ in range(2):
        monitor = fcl.Monitor(formula, 2)
        monitor.start({"p": False})
        monitor.step({"p": False})
        assert len(monitor.step({"p": False})) == 1
