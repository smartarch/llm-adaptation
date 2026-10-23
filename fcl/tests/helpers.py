from typing import Any

import fcl


def run_trace(formula_text: str, states: list[dict[str, Any]], finish_after: int | None = None) -> list[fcl.Violation]:
    """Monitor the formula over a hand-made trace and return all violations (including those found at the end).

    `states[0]` is the initial state s_0, `states[1:]` are the states s_1, ..., s_k (so `trace_length = len(states) - 1`).
    If `finish_after` is given, the trace ends prematurely after that many steps.
    """
    trace_length = len(states) - 1
    monitor = fcl.Monitor(fcl.parse(formula_text), trace_length)
    violations = monitor.start(states[0])
    steps = states[1:] if finish_after is None else states[1:finish_after + 1]
    for state in steps:
        violations += monitor.step(state)
    violations += monitor.finish()
    return violations


def trace(**columns: list) -> list[dict[str, Any]]:
    """Build a trace from columns, e.g. `trace(p=[True, False], q=[0, 1])` (the first value is the initial state)."""
    length = len(next(iter(columns.values())))
    return [{name: values[i] for name, values in columns.items()} for i in range(length)]


def steps_of(violations: list[fcl.Violation]) -> list[int]:
    return [v.step for v in violations]
