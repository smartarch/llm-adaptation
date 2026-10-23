# FCL: Functional Constraints Logic

`fcl` is a small, self-contained Python package for **parsing** FCL formulas and **monitoring** them online over a finite trace of system states. It does not depend on the simulator. The only dependency is [`lark`](https://github.com/lark-parser/lark).

It is a simplified version of the FCL presented in the paper. As explained in the paper, this subset currently only supports online monitoring of the traces which does not correctly check the end of a prematurely terminated trace. Another big simplification is that we use Python expressions instead of logical formulas for the predicates. This makes it easier to evaluate them without the need for a full logical evaluation engine. These simplifications are sufficient for all the functional constraints presented in the paper. A full implementation of FCL can be implemented in the future if needed.

It is used by the simulator ([`DSL/constraints/constraint.py`](../DSL/constraints/constraint.py)) to check the functional constraints of the adaptation manager. It can be used on its own for any system that produces a sequence of states.

## Quick start

```python
import fcl

# whenever `x` gets marked, it must be done within the next 2 states
formula = fcl.parse("always(forall x in `xs`: `x in marked` implies within(1, 2, `x in done`))")

states = [
    {"xs": [1, 2], "marked": set(), "done": set()},   # s_0: initial state
    {"xs": [1, 2], "marked": {1, 2}, "done": set()},  # s_1
    {"xs": [1, 2], "marked": set(), "done": {1}},     # s_2
    {"xs": [1, 2], "marked": set(), "done": set()},   # s_3
]
monitor = fcl.Monitor(formula, trace_length=len(states) - 1)
violations = monitor.start(states[0])
for state in states[1:]:
    violations += monitor.step(state)
violations += monitor.finish()

for v in violations:
    print(v.step, v.bindings, v.trigger_step, v.formula)
# -> 3 {'x': 2} 1 within(1, 2, `x in done`)
```

## Syntax

For simplicity, predicates are Python expressions in backticks. They are evaluated with `eval` in the current state, together with the variables bound by `forall` and the constants `MAX` and `BEG`.

```text
formula     := predicate | within | always | forall | implication
predicate   := `python expression`
within      := within(n, t, predicate)
always      := always(formula)                         # body must not contain another always
forall      := forall NAME in `python set expression`: formula
implication := antecedent implies consequent
antecedent  := predicate | within with t < 0           # past window
consequent  := predicate | within with t > 0           # future window
n, t        := INTEGER | MAX | BEG | `python expression`
```

The grammar is in [`grammar.lark`](./grammar.lark). Syntax errors raise `lark.exceptions.LarkError`. Formulas outside the implemented subset raise `fcl.FCLError`, e.g. a future `within` in an antecedent, or nested `always`.

## Semantics

### Trace

* The trace consists of the **initial state** `s_0` and the states `s_1, ..., s_k`, where `k` is the `trace_length`.
  * In the simulator, `s_0` is the system before the first adaptation (no ensembles assigned).
  * `s_i` is the state in adaptation step `i`, including the assignment proposed in that step.
* **Constants**, in the state `s_i`:
  * `MAX = k - i`: the number of remaining states;
  * `BEG = i`: the number of previous states.
* **The top-level formula is evaluated only in `s_0`.** Temporal operators look at the other states.
  * A top-level predicate is checked only in `s_0`.
  * A top-level `forall` ranges over the elements of the set in `s_0`.

### Operators

* **`within(n, t, p)` with `t > 0`** (future window):
  * `p` must hold in at least `n` of the next `t` states, `s_{i+1} .. s_{i+t}`. The window is strict: the current state is not part of it.
  * The window is truncated at the end of the trace, i.e. it has `min(t, MAX)` states.
  * Evaluating it creates a *temporal obligation*. The obligation is satisfied as soon as `p` has held `n` times, and violated as soon as `n` cannot be reached any more in the rest of the window.
  * If `n <= 0`, it is trivially satisfied. If the window has fewer than `n` states, it is violated immediately; for example, an obligation created in the last state has an empty window. Use a guard such as `MAX > 0` in the antecedent to avoid this.
* **`within(n, t, p)` with `t < 0`** (past window):
  * `p` must have held in at least `n` of the previous `|t|` states, `s_{i-|t|} .. s_{i-1}`. Again the window is strict.
  * The history is kept separately for each binding of the `forall` variables. It starts with the first state in which the window is evaluated for that binding, which truncates the window for, e.g., components that appeared later.
* **`within(n, 0, p)`**: an empty window, true if and only if `n <= 0`.
* **`always(φ)`** = `within(MAX, MAX, φ)`: `φ` is evaluated in every following state `s_{i+1} .. s_k`.
  * It is the only operator whose body can be a formula (`forall`, an implication, `within`, ...), not just a predicate.
  * A temporal operator inside `always` is evaluated in every state. For example, `always(a implies within(1, 3, b))` creates a new obligation in every state in which `a` holds.
  * Sets inside `always` are re-evaluated in every state, so `always(forall x in S: ...)` also covers elements that are added to `S` later.
* **`a implies c`**: if `a` holds, then `c` is evaluated (a predicate is checked, a future `within` creates an obligation).
  * Obligations already created are evaluated in every following state, regardless of the antecedent.
* **`forall x in S: φ`**: `φ` is evaluated for each element of `S`. The bindings are part of the reported violations.
* **Numbers** given by a Python expression are rounded up (e.g. ``within(`0.8 * MAX`, MAX, ...)`` requires ⌈0.8 · MAX⌉ occurrences).

### End of the trace

* **Only the regular end of the trace is supported**, i.e. after `trace_length` calls of `step`. All obligations are resolved by then, because their windows are truncated by `MAX`.
* **A premature end** (calling `finish` earlier) is not supported by the online monitor.
  * With a shorter trace, `MAX` would have been smaller, so different obligations would have been created, e.g. ones guarded by `MAX > 0`.
  * The pending obligations are therefore discarded without a verdict. Violations reported before the premature end remain valid.
  * In the Dragon Hunt, a premature end means the Dragon was killed, i.e. the game was won.

### Removed objects

`Monitor.step(state, existing_objects=...)` discards the pending obligations (and `always` instances) bound by `forall` to an object that is not in `existing_objects`. For example, a villager that died cannot satisfy its obligations any more.

## API

* **`fcl.parse(text) -> Formula`** parses a formula. The AST is immutable, so the same formula can be monitored repeatedly.
* **`fcl.Monitor(formula, trace_length)`** is the online monitor of one trace:
  * `start(initial_state) -> list[Violation]`: evaluate the formula in `s_0`;
  * `step(state, existing_objects=None) -> list[Violation]`: process the next state;
  * `finish() -> list[Violation]`: end of the trace (see above);
  * `is_complete`: whether all `trace_length` states have been processed.
* **`fcl.State`** = `Mapping[str, Collection | Any]`. It maps the names used in the predicates to values.
  * Sets (components of a type, members of an ensemble, ...) can be any set-like collection supporting `in`, `len` and iteration.
  * `MAX` and `BEG` are added by the monitor.
* **`fcl.Violation`** describes one detected violation:
  * `step`: the index of the state where it was detected;
  * `bindings`: the values of the `forall` variables;
  * `state`: the state at detection;
  * `formula`: the violated subformula as text.

  For violated obligations it also has:
  * `trigger_step` and `trigger_state`: where the obligation was created;
  * `required` and `occurred`: the required and actual number of occurrences.

  Turning a violation into a human-readable message is left to the caller. For example, the simulator formats a `reason` string with the violation's state and bindings.

## Examples

| Requirement | FCL |
| --- | --- |
| The Dragon is killed | `` within(1, MAX, `dragon.hp <= 0`) `` |
| The Dragon is attacked in the first 15 steps | `` within(1, 15, `len(AttackEn) > 0`) `` |
| Fields are never overprotected (the fields are fixed) | ``forall f in `FieldComps`: always(`len(ProtectingEns[f]) <= f.drones_for_full_protection`)`` |
| Farmers (also the newly spawned ones) stay in the Village | ``always(forall f in `Farmers`: `f.location == Map.VILLAGE`)`` |
| After moving to the Cave, a warrior attacks | ``always(forall w in `Warriors`: `w in GoToCaveEn and MAX > 0` implies within(1, MAX, `w in AttackEn`))`` |
| A drone with low battery starts charging within 3 steps | ``always(forall d in `DroneComps`: `d.battery <= 0.2 and d not in ChargingEn and MAX > 0` implies within(1, 3, `d in ChargingEn`))`` |
| The Dragon is never left unattacked for 3 steps in a row | ``always(within(2, -2, `len(AttackEn) == 0`) implies `len(AttackEn) > 0`)`` |
| Spawn new warriors at least twice | `` within(2, MAX, `len(SpawnWarriorEn) >= 2`) `` |
| The idle drones are at most half of all the drones in 80 % of the states | `` within(`0.8 * MAX`, MAX, `len(IdleEn) <= len(DroneComps) / 2`) `` |

## Tests

```bash
pytest fcl/tests
```

The tests run on hand-made traces and do not need the simulator.
