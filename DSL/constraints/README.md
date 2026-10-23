# Functional constraints in the DSL

The functional (user) constraints are defined in the `*_constraints.yaml` files next to the architecture specification (e.g. [`DSL/dragon_constraints.yaml`](../dragon_constraints.yaml)). They are evaluated with the [`fcl`](../../fcl/README.md) package, which documents the syntax and semantics of the formulas.

## Definition of a constraint

```yaml
constraints:                       # global constraints (see all components and ensembles)
  attack_after_moving_to_cave:     # name of the constraint
    variables:                     # optional, evaluated (in order) in every step with Python `eval`
      Warriors: "[v for v in VillagerComps if v.role == 'Warrior']"
    constraint: "always(forall warrior in `Warriors`: `warrior in GoToCaveEn and MAX > 0` implies within(1, MAX, `warrior in AttackEn`))"
    reason: "Warrior {warrior.name} should attack the Dragon after moving to the Cave."
```

* Constraints can also be defined per assignment (`assignments.<name>.constraints`). They then see only the components and ensembles of that assignment. For example, `VillagerComps` in a constraint of `assign_in_village` holds only the villagers in the Village.
* Each simulation run is one monitored trace:
  * the initial state `s_0` is the system before the first adaptation, with all ensembles empty;
  * the state of step `i` includes the assignment proposed by the AM in that step;
  * the trace length is the number of steps of the run.

  Constraint evaluation is skipped while arranging the initial state of a test situation (`Simulation.user_constraints_enabled`).
* `reason` is a Python f-string. It is used as the feedback message when the constraint is violated, and it is formatted with:
  * the state in which the violation was detected;
  * the quantified variables (e.g. `{warrior}`);
  * `step`, `trigger_step` and `trigger_state`.

## Names available in the state

[`UserConstraint.prepare_context`](./constraint.py) builds the state passed to the FCL monitor:

* **Components:** `<Type>Comps` is the list of all components of the type, e.g. `VillagerComps`, `FieldComps`.
* **Ensembles:**
  * `<Type>Ens` is a dict of the ensemble instances indexed by their parameter, for ensemble types with parameters (e.g. `ProtectingEns[field]`);
  * `<Type>En` is the ensemble instance, for singleton ensembles (e.g. `AttackEn`).

  Ensembles support `len(...)`, `in` and iteration.
* **The simulator's globals** (`Simulation.get_globals()`), e.g. `environment`, `Map`, `DroneState`.
* **The variables** defined in `variables`.
* **`step`:** the current simulation step.
* **`MAX` and `BEG`:** added by the FCL monitor, available in the formula's predicates but not in `variables`.

## Feedback

The violations are reported as `UserConstraintError`s, with the constraint name and the step. The functional tests in [`generated_adaptations/tests/test_generic.py`](../../generated_adaptations/tests/test_generic.py) group them by constraint. For each constraint, at most 3 distinct messages are shown, followed by a summary such as "(violated 17 times in total, at steps 4, 5, 6, ...)".
