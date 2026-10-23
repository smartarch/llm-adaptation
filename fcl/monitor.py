"""Online monitor of FCL formulas.

The monitored trace consists of the initial state s_0 (passed to `Monitor.start`) and the states s_1, ..., s_k
(passed to `Monitor.step`), where k is the `trace_length`. In the state s_i, the constants are `MAX = k - i`
(number of remaining states) and `BEG = i` (number of previous states).
"""
import dataclasses
import math
from collections import defaultdict
from typing import Any, Collection, Iterable, Mapping

from fcl.ast import Always, FCLError, ForAll, Implies, Node, Num, Pred, Within
from fcl.utils import HashableDict

Formula = Node
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
    """Index of the state in which the violation was detected (0 = initial state)."""
    bindings: Mapping[str, Any]
    """Values of the quantified variables (`forall`) for which the violation occurred."""
    state: State
    """State in which the violation was detected (including `MAX` and `BEG`)."""
    formula: str
    """Text representation of the violated (sub)formula."""
    trigger_step: int | None = None
    """Index of the state in which the violated temporal obligation was created (None if not caused by an obligation)."""
    trigger_state: State | None = None
    """State in which the violated temporal obligation was created (None if not caused by an obligation)."""
    required: int | None = None
    """Required number of occurrences of the obligation (None if not caused by an obligation)."""
    occurred: int | None = None
    """Number of occurrences of the obligation (None if not caused by an obligation)."""


@dataclasses.dataclass(eq=False)
class _Obligation:
    """Pending future `within` created in the state `created` (its window is `created + 1 .. window_end`)."""
    node: Within
    bindings: dict[str, Any]
    created: int
    trigger_state: State
    required: int
    window_end: int
    occurred: int = 0


class Monitor:
    """Online monitor of an FCL formula over a trace of a known length.

    Usage: `start(initial_state)`, then `step(state)` for each of the `trace_length` states, then `finish()`.
    """

    def __init__(self, formula: Formula, trace_length: int):
        if trace_length < 0:
            raise ValueError("trace_length must be non-negative")
        self.formula = formula
        self.trace_length = trace_length
        self.index: int | None = None  # index of the last processed state
        self.obligations: list[_Obligation] = []
        self.always_instances: list[tuple[Always, dict[str, Any]]] = []
        self.history: dict[tuple[int, HashableDict], list[tuple[int, bool]]] = defaultdict(list)

    # --- public API ---

    def start(self, state: State) -> list[Violation]:
        """Evaluate the formula in the initial state s_0 and return the detected violations."""
        if self.index is not None:
            raise RuntimeError("Monitor.start() can be called only once.")
        self.index = 0
        env = self._env(state)
        violations: list[Violation] = []
        self._evaluate(self.formula, env, {}, violations)
        return violations

    def step(self, state: State, existing_objects: Iterable[Any] | None = None) -> list[Violation]:
        """Process the next state of the trace and return the detected violations.

        If `existing_objects` is given, pending obligations (and `always` instances) bound (by `forall`) to an
        object that is not among them are discarded, e.g. when a component has been removed from the system.
        """
        if self.index is None:
            raise RuntimeError("Monitor.start() must be called before Monitor.step().")
        if self.index >= self.trace_length:
            raise RuntimeError(f"The trace is longer than trace_length ({self.trace_length}).")
        self.index += 1
        env = self._env(state)
        violations: list[Violation] = []

        if existing_objects is not None:
            self._discard_bindings_not_in(existing_objects)

        # advance the pending obligations (created in the previous states)
        pending = []
        for obligation in self.obligations:
            verdict = self._advance(obligation, env)
            if verdict is None:
                pending.append(obligation)
            elif verdict is False:
                violations.append(self._obligation_violation(obligation, env))
        self.obligations = pending

        # evaluate the bodies of `always` (they may create new obligations, which start in the next state)
        for node, bindings in list(self.always_instances):
            self._evaluate(node.body, env, bindings, violations)

        return violations

    def finish(self) -> list[Violation]:
        """Finish the monitoring at the end of the trace.

        At the regular end of the trace (after `trace_length` steps), all obligations are already resolved.
        A premature end (fewer steps) is not supported by the online monitor: the pending obligations are
        discarded without a verdict (with a shorter trace, `MAX` would be smaller, so different obligations
        would have been created).
        """
        if self.index is None or self.index < self.trace_length:
            self.obligations = []
            return []
        # cannot happen (all windows end at the latest in the last state), kept as a safety net
        violations = [self._obligation_violation(o, o.trigger_state) for o in self.obligations if o.occurred < o.required]
        self.obligations = []
        return violations

    @property
    def is_complete(self) -> bool:
        """Whether all `trace_length` states have been processed."""
        return self.index is not None and self.index >= self.trace_length

    # --- evaluation ---

    def _env(self, state: State) -> dict[str, Any]:
        assert self.index is not None
        return dict(state) | {"MAX": self.trace_length - self.index, "BEG": self.index}

    def _evaluate(self, node: Node, env: dict[str, Any], bindings: dict[str, Any], violations: list[Violation]):
        """Evaluate a formula in the current state; violations are appended to `violations`."""
        if isinstance(node, Pred):
            if not self._holds(node, env, bindings):
                violations.append(self._violation(node, env, bindings))
        elif isinstance(node, Within):
            t = self._resolve(node.t, env, bindings)
            if t > 0:
                self._create_obligation(node, env, bindings, violations)
            elif not self._past(node, t, env, bindings):
                violations.append(self._violation(node, env, bindings))
        elif isinstance(node, Always):
            self.always_instances.append((node, bindings))
        elif isinstance(node, Implies):
            if self._antecedent_holds(node.left, env, bindings):
                self._evaluate_consequent(node.right, env, bindings, violations)
        elif isinstance(node, ForAll):
            for element in self._eval(node.set_expr, env, bindings) or []:
                self._evaluate(node.body, env, bindings | {node.var: element}, violations)
        else:
            raise FCLError(f"Unsupported formula: {node}")

    def _antecedent_holds(self, node: Node, env: dict[str, Any], bindings: dict[str, Any]) -> bool:
        if isinstance(node, Pred):
            return self._holds(node, env, bindings)
        if isinstance(node, Within):
            t = self._resolve(node.t, env, bindings)
            if t > 0:
                raise FCLError(f"Antecedent of an implication must be a past within (t < 0): {node}")
            return self._past(node, t, env, bindings)
        raise FCLError(f"Unsupported antecedent: {node}")

    def _evaluate_consequent(self, node: Node, env: dict[str, Any], bindings: dict[str, Any], violations: list[Violation]):
        if isinstance(node, Within) and self._resolve(node.t, env, bindings) < 0:
            raise FCLError(f"Consequent of an implication must be a future within (t > 0): {node}")
        if not isinstance(node, (Pred, Within)):
            raise FCLError(f"Unsupported consequent: {node}")
        self._evaluate(node, env, bindings, violations)

    def _create_obligation(self, node: Within, env: dict[str, Any], bindings: dict[str, Any], violations: list[Violation]):
        assert self.index is not None
        required = self._resolve(node.n, env, bindings)
        if required <= 0:
            return  # trivially satisfied
        t = self._resolve(node.t, env, bindings)
        window_end = self.index + min(t, env["MAX"])
        obligation = _Obligation(node, bindings, self.index, env, required, window_end)
        if window_end - self.index < required:  # the (truncated) window is too short
            violations.append(self._obligation_violation(obligation, env))
        else:
            self.obligations.append(obligation)

    def _advance(self, obligation: _Obligation, env: dict[str, Any]) -> bool | None:
        """Evaluate the obligation in the current state; returns True/False when resolved, None if still pending."""
        assert self.index is not None
        if self._holds(obligation.node.pred, env, obligation.bindings):
            obligation.occurred += 1
        if obligation.occurred >= obligation.required:
            return True
        remaining = obligation.window_end - self.index
        if obligation.required - obligation.occurred > remaining:
            return False
        return None

    def _past(self, node: Within, t: int, env: dict[str, Any], bindings: dict[str, Any]) -> bool:
        """Evaluate a past (or empty, t = 0) window and record the predicate value of the current state."""
        assert self.index is not None
        required = self._resolve(node.n, env, bindings)
        history = self.history[(id(node), HashableDict(bindings))]
        first = self.index + t  # t <= 0
        occurred = sum(1 for index, value in history if index >= first and value)
        history.append((self.index, self._holds(node.pred, env, bindings)))
        return occurred >= required

    def _discard_bindings_not_in(self, existing_objects: Iterable[Any]):
        existing = {id(o) for o in existing_objects}

        def exists(bindings: dict[str, Any]) -> bool:
            return all(id(value) in existing for value in bindings.values())

        self.obligations = [o for o in self.obligations if exists(o.bindings)]
        self.always_instances = [(node, b) for node, b in self.always_instances if exists(b)]

    # --- helpers ---

    @staticmethod
    def _eval(pred: Pred, env: dict[str, Any], bindings: dict[str, Any]) -> Any:
        return eval(pred.code, env | bindings)

    def _holds(self, pred: Pred, env: dict[str, Any], bindings: dict[str, Any]) -> bool:
        return bool(self._eval(pred, env, bindings))

    def _resolve(self, num: Num, env: dict[str, Any], bindings: dict[str, Any]) -> int:
        if isinstance(num, int):
            return num
        if num in ("MAX", "BEG"):
            return env[num]  # type: ignore[index]
        return math.ceil(self._eval(num, env, bindings))  # type: ignore[arg-type]

    def _violation(self, node: Node, env: dict[str, Any], bindings: dict[str, Any]) -> Violation:
        assert self.index is not None
        return Violation(step=self.index, bindings=dict(bindings), state=env, formula=str(node))

    def _obligation_violation(self, obligation: _Obligation, env: dict[str, Any]) -> Violation:
        assert self.index is not None
        return Violation(
            step=self.index,
            bindings=dict(obligation.bindings),
            state=env,
            formula=str(obligation.node),
            trigger_step=obligation.created,
            trigger_state=obligation.trigger_state,
            required=obligation.required,
            occurred=obligation.occurred,
        )
