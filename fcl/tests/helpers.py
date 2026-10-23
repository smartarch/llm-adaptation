from typing import Any

import fcl


def run_trace(formula_text: str, states: list[dict[str, Any]]) -> list[fcl.Violation]:
    """Monitor the formula over a hand-made trace and return all violations (including those found at the end).

    Mimics the current simulator: steps are numbered from 1 and `MAX` is the number of remaining steps
    including the current one (provided in the state by the caller).
    """
    monitor = fcl.Monitor(fcl.parse(formula_text))
    steps = len(states)
    violations = []
    for step, state in enumerate(states, start=1):
        violations += monitor.step(state | {"MAX": steps - step + 1}, step)
    violations += monitor.finish(states[-1] | {"MAX": 1}, steps)
    return violations


def trace(**columns: list) -> list[dict[str, Any]]:
    """Build a trace from columns, e.g. `trace(p=[True, False], q=[0, 1])`."""
    length = len(next(iter(columns.values())))
    return [{name: values[i] for name, values in columns.items()} for i in range(length)]
