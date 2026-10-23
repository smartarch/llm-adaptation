# FCL: Functional Constraints Logic

`fcl` is a small, self-contained Python package for **parsing** FCL formulas and **monitoring** them online over a sequence of system states. It does not depend on the simulator. The only dependency is [`lark`](https://github.com/lark-parser/lark).

It is used by the simulator ([`DSL/constraints/constraint.py`](../DSL/constraints/constraint.py)) to check the functional constraints of the adaptation manager. It can be used on its own for any system that produces a sequence of states.

## Quick start

```python
import fcl

formula = fcl.parse("forall x in `xs`: always(`x not in bad`)")
monitor = fcl.Monitor(formula)

states = [
    {"xs": [1, 2], "bad": set()},
    {"xs": [1, 2], "bad": {2}},
]
steps = len(states)
for step, state in enumerate(states, start=1):
    for violation in monitor.step(state | {"MAX": steps - step + 1}, step):
        print(violation.step, violation.bindings)   # -> 2 {'x': 2}
for violation in monitor.finish(states[-1] | {"MAX": 1}, steps):
    print(violation)
```

## API

* **`fcl.parse(text) -> Formula`** parses a formula written in the syntax below.
  * Note that a parsed formula keeps the evaluation state (obligations, history), so it can be monitored only once. Parse the formula again for each run.
* **`fcl.Monitor(formula)`** is the online monitor.
  * `step(state, step) -> list[Violation]`: evaluate the formula in the state of the given step.
  * `finish(state, step) -> list[Violation]`: call once at the end of the run to evaluate the pending temporal obligations.
* **`fcl.State`** = `Mapping[str, Collection | Any]`. It maps the names used in the formula's Python expressions to values.
  * Sets (components of a type, members of an ensemble, ...) can be any set-like collection supporting `in`, `len` and iteration.
  * The constant `MAX` (the number of remaining steps, including the current one) currently has to be provided by the caller.
* **`fcl.Violation`** describes one detected violation:
  * `step`: the step where it was detected;
  * `bindings`: the values of the variables quantified by `forall`;
  * `state`: the state at detection;
  * `formula`: a text representation of the violated (sub)formula;
  * for violated temporal obligations, also `trigger_step`, `required` and `occurred`.

  Turning a violation into a human-readable message is left to the caller. For example, the simulator formats a `reason` string with the violation's state and bindings.

## Syntax

Predicates are Python expressions in backticks. They are evaluated with `eval` in the given state (plus the bindings of quantified variables).

```text
formula     := predicate | temporal | forall | implication
predicate   := `python expression`
temporal    := within(n, t, predicate)       # predicate holds at least n times within the next t steps
             | scattered(n, predicate)        # = within(n, MAX, predicate)
             | consequent(t, predicate)       # = within(t, t, predicate)
             | always(predicate)              # = within(MAX, MAX, predicate)
             | once(predicate)                # = within(1, MAX, predicate)
             | next(predicate)                # = within(1, 1, predicate)
implication := (predicate | temporal) implies (predicate | temporal)
forall      := forall NAME in `python set expression`: (predicate | temporal | implication)
n, t        := NUMBER | MAX | `python expression`
```

The grammar is in [`grammar.lark`](./grammar.lark).

## Semantics (current implementation)

* **`within(n, t, p)`** creates a *temporal obligation*. It counts the states in which `p` holds over the window of `t` steps starting with the current step, and it is violated if fewer than `n` such states occur.
  * It is resolved as violated as soon as `n` cannot be reached any more, otherwise at the end of the window.
  * Obligations still pending at the end of the run are evaluated by `Monitor.finish`.
* **A temporal operator in the antecedent of an implication** is evaluated over the history (the last `t` steps, including the current one) instead of creating an obligation.
* **`forall x in S: φ`** evaluates `φ` for each element of `S`, and obligations are kept separately for each binding. The set `S` is re-evaluated in every step, so elements that appear later are also checked.

Known issues, which will be fixed:

* the consequent's obligation is created even when the antecedent does not hold;
* a violation of the consequent can be lost when the antecedent is false at the step the obligation fails;
* windows include the current step (they are not strict).

The issues are covered by the `xfail` tests in [`tests/test_monitor.py`](./tests/test_monitor.py).

## Examples

| Requirement | FCL |
| --- | --- |
| The Dragon should be attacked at least once in the first 15 steps | `` within(1, 15, `len(AttackEn) > 0`) `` |
| No field is ever overprotected | ``forall field in `FieldComps`: always(`len(ProtectingEns[field]) <= field.drones_for_full_protection`)`` |
| Spawn new warriors at least twice | `` scattered(2, `len(SpawnWarriorEn) >= 2`) `` |
| At least half of the warriors are in the Cave 80 % of the time | `` scattered(`0.8 * MAX`, `len([w for w in Warriors if w.location == Map.CAVE]) >= 0.5 * len(Warriors)`) `` |

## Tests

```bash
pytest fcl/tests
```

The tests run on hand-made traces and do not need the simulator.
