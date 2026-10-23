import dataclasses
from typing import Any, Collection, Mapping

from fcl.ast import ASTNode, ForAllViolation, TemporalObligation

Formula = ASTNode
"""A parsed FCL formula (see `fcl.parse`)."""

State = Mapping[str, Collection[Any] | Any]
"""The state of the system in one step: maps names used in the formula to values.

Sets (e.g., components of a type or members of an ensemble) can be any set-like collection
supporting `in`, `len` and iteration. Other values (constants, single components, ...) can be arbitrary.
"""


@dataclasses.dataclass(frozen=True)
class Violation:
    """A violation of a formula detected by the `Monitor`."""
    step: int
    """Step in which the violation was detected."""
    bindings: Mapping[str, Any]
    """Values of the quantified variables (`forall`) for which the violation occurred."""
    state: State
    """State in which the violation was detected."""
    formula: str
    """Text representation of the violated (sub)formula."""
    trigger_step: int | None = None
    """Step in which the violated temporal obligation was created (None if not caused by an obligation)."""
    trigger_state: State | None = None
    """State in which the violated temporal obligation was created (None if not available)."""
    required: int | None = None
    """Required number of occurrences of the obligation (None if not caused by an obligation)."""
    occurred: int | None = None
    """Number of occurrences of the obligation (None if not caused by an obligation)."""


class Monitor:
    """Online monitor of an FCL formula.

    Call `step` for each step of the system and `finish` once at the end of the run.
    """

    def __init__(self, formula: Formula):
        self.formula = formula
        self.obligations: list[TemporalObligation] = []

    def step(self, state: State, step: int) -> list[Violation]:
        """Evaluate the formula in the given state and return the detected violations."""
        violations = []
        result = self.formula.evaluate(step, dict(state), {})
        if isinstance(result, list):
            for r in result:
                if isinstance(r, TemporalObligation):
                    if r not in self.obligations:
                        self.obligations.append(r)
                elif isinstance(r, ForAllViolation):
                    violations.append(Violation(step=step, bindings=r.bindings, state=r.context, formula=repr(self.formula)))
        if result is False:
            violations.append(Violation(step=step, bindings={}, state=state, formula=repr(self.formula)))
        return violations

    def finish(self, state: State, step: int) -> list[Violation]:
        """Evaluate the pending obligations at the end of the run and return the detected violations."""
        violations = []
        for obligation in self.obligations:
            if not obligation.resolved and step >= obligation.end_step and obligation.occurrences < obligation.min_occurrences:
                violations.append(Violation(
                    step=step,
                    bindings=obligation.bound_variables,
                    state=state,
                    formula=repr(obligation),
                    trigger_step=obligation.start_step,
                    required=obligation.min_occurrences,
                    occurred=obligation.occurrences,
                ))
        return violations
