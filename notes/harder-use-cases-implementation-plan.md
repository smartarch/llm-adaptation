# Implementation plan: FCL module, verifier fixes, harder Dragon Hunt and Smart Farm

## Context

Newer LLMs solve both use cases on the first attempt, so the vibe-coding feedback loop never runs (see [notes/harder-use-cases-plan.md](notes/harder-use-cases-plan.md)). We make both examples harder: meals and Dragon regeneration for the Dragon Hunt, batteries and charging for the Smart Farm.

The new constraints need FCL features the verifier does not support: repeatedly armed obligations, `always` around implications, strict past windows. The verifier also has confirmed bugs, for example `attack_after_moving_to_cave` can never fail.

At the same time, FCL is split out of the simulator into a reusable Python package.

**Goals:**

1. Split FCL from the simulator.
2. Fix the bugs and extend FCL.
3. Make the Dragon Hunt harder.
4. Make the Smart Farm harder.

**Extra goals, added from the analysis:**

* fix the context problems found while exploring (listed in Phase 2);
* update the prompts;
* write reference baselines;
* keep the docs and the notes in sync.

**Decisions already made:**

* **Initial state.** s₀ is a virtual state before the first adaptation. It has the components of the simulation's initial state, and all ensembles are empty. `always(φ)` ≡ `within(MAX, MAX, φ)`, which covers the adaptation steps 1..k.
* **No commits by me.** After each phase I stop and report in the chat:
  * what was done;
  * whether it went according to the plan;
  * any deviations or additional changes;
  * the verification results.

  You review the changes and commit them yourself (leaving `scales.xlsx` and the untracked result folders alone), then tell me to continue with the next phase.
* **Levels.** Level 0 and Level 1 are not kept strictly separate. All new mechanics are parameterised through config files.

**Step 0, after this plan is approved:** copy this plan to `notes/harder-use-cases-implementation-plan.md`, next to `notes/harder-use-cases-plan.md`.

**Test commands** used throughout. They are run from the repository root with `PYTHONPATH` set to it, as in [generated_adaptations/README.md](generated_adaptations/README.md).

```bash
# T(<example>, <mock>, <tests>), where <tests> is system or functional
pytest generated_adaptations/tests -q --tb=short -rfExX --show-capture=no --color=no --example=<example> --adaptation_name=<mock> --variant=mock --tests=<tests>
```

The **mock AMs** are:

* dragon: `baseline`, which is renamed to `greedy_no_meals` in Phase 3; the snapshots from Phase 3 on use the new name;
* farm: `random_adapt`, `all1_adapt`, `assign_except_moving`, `most_threatened`, `protect_by_threat`.

The **"snapshot"** is `T` for every mock × {`system`, `functional`}, i.e. 12 runs. Each output is saved to the scratchpad under `<phase>/<example>_<mock>_<tests>.txt`, so it can be compared with `diff`.

---

## Phase 1: Split FCL into a standalone package (pure refactoring)

Behaviour stays identical, bugs included, so the test reports must not change. The semantic changes come in Phase 2, which keeps the diffs easy to verify.

### New package `fcl/` (depends only on `lark`)

* **`fcl/__init__.py`** exports `parse`, `Monitor`, `Violation`, `Formula`, `State`.
* **`fcl/grammar.lark`**: the current `DSL/constraints/grammar-simple.lark`, unchanged. The unused `grammar.lark` is deleted; it stays in git history.
* **`fcl/parser.py`**: `ConstraintParser` and `ConstraintASTTransformer` moved from [DSL/constraints/parser.py](DSL/constraints/parser.py). `parse_constraint` becomes `fcl.parse`.
* **`fcl/ast.py`**: the nodes moved from [DSL/constraints/evaluation.py](DSL/constraints/evaluation.py) (`PyExpr`, `TemporalWithin`, `TemporalObligation`, `TemporalHistory`, `Implies`, `ForAll`, `resolve_number`).
* **`fcl/utils.py`**: `HashableDict`, moved from [utils.py:130-132](utils.py#L130-L132). It is used only by the FCL code, so it is removed from `utils.py`.
* **`fcl/monitor.py`**: the obligation bookkeeping now spread over [constraint.py](DSL/constraints/constraint.py) (`obligations` list, `check_end`, `ForAllViolation` handling) moves into one class:

  ```python
  State = Mapping[str, Collection[Any] | Any]   # names -> set-like values (ensembles, component sets) or plain values

  class Monitor:
      def __init__(self, formula: Formula): ...
      def step(self, state: State, step: int) -> list[Violation]: ...
      def finish(self, state: State, step: int) -> list[Violation]: ...

  @dataclass(frozen=True)
  class Violation:
      step: int                    # step where the violation was detected
      trigger_step: int | None     # step where the obligation was created (None for plain predicates)
      bindings: Mapping[str, Any]  # quantified variables, e.g. {"warrior": <Villager>}
      state: State                 # state at the detection step
      trigger_state: State | None  # state at the trigger step
      formula: str                 # text of the failed sub-formula (for debugging and structured feedback)
      required: int | None         # n of the window
      occurred: int | None         # how often the predicate held
  ```

  In Phase 1 the interface intentionally has no initial state and no `trace_length`. As today, `MAX` is provided by the caller in `state` (from `Simulation.get_globals()`), and the first `step()` is the first adaptation step.

  Phase 2 extends the constructor to `Monitor(formula, trace_length)` and adds `start(initial_state)` for the virtual s₀. FCL then computes `MAX` itself.
* **`fcl/tests/`**: plain pytest unit tests on hand-made traces, run with `pytest fcl/tests`, with no simulator. They cover parsing every operator and the current evaluation behaviour. The confirmed bugs are encoded as `xfail(strict=True)` tests: the two traces from §B.1 of the notes, plus the off-by-one. They must turn green in Phase 2.
* **`fcl/README.md`**: basic documentation. It covers:
  * the purpose of the package;
  * syntax and semantics (moved from [DSL/constraints/constraints.md](DSL/constraints/constraints.md));
  * the API (`parse`, `Monitor.step/finish`, `Violation`, what `State` must contain);
  * a minimal example of driving a monitor over a list of states;
  * the restrictions of the implemented subset.

  It is updated again in Phase 2.

### Simulator side

* [DSL/constraints/constraint.py](DSL/constraints/constraint.py) keeps `UserConstraint`, which:
  * builds the state (`prepare_context`: `<Type>Comps`, `<Type>En`, `<Type>Ens`, YAML `variables`, globals);
  * owns an `fcl.Monitor`;
  * turns each `Violation` into a reason by evaluating the f-string in the context `violation.state | violation.bindings | {"step": ..., "trigger_step": ..., "trigger_state": ...}`.

  The existing reasons use bindings (`{warrior}`, `{field.id}`) and detection-step values (`{len(ProtectingEns[field])}`, `{most_threatened_field.id}`, `{average_coverage}`), so the detection state is the default context. The trigger state is still available for response-type reasons.
* `DSL/constraints/` keeps only `constraint.py` and a short README with the DSL-specific part of `constraints.md`: context names, `variables`, `reason`.
* [DSL/dsl_utils.py:52-66](DSL/dsl_utils.py#L52-L66) switches to `fcl.parse` and drops the debug `print(ast)`.
* [base_classes/simulation.py](base_classes/simulation.py) is unchanged in Phase 1.

### Verification (Phase 1)

1. **Before any change**, take the snapshot `before/`: all mocks × {system, functional}, as defined above.
2. **After the refactoring**, take the snapshot `phase1/` and `diff` it against `before/`. The outputs must be identical, apart from timing lines.
3. `pytest fcl/tests`: all pass, and the bug tests are reported as xfail.
4. Stop and report (no commit).

---

## Phase 2: FCL semantics, bug fixes and new features

### Grammar (`fcl/grammar.lark`): minimal and close to the logic

```
start       : formula
formula     : forall | always | implication | within | py_expr
forall      : "forall" NAME "in" py_expr ":" formula          # nesting of forall allowed
always      : "always" "(" formula ")"                         # □φ ≡ within(MAX, MAX, φ); body may contain within/implication/forall
within      : "within" "(" num "," num "," py_expr ")"         # t > 0 future, t < 0 past (new: signed numbers)
implication : (py_expr | within) "implies" (py_expr | within)   # antecedent: predicate or PAST within; consequent: predicate or FUTURE within
num         : SIGNED_NUMBER | "MAX" | "BEG" | py_expr
```

* **Removed:** `once`, `scattered`, `consequent`, `next`.
* **Kept:** `always`, as its own keyword. It is the only place where a formula (not just a predicate) is allowed inside a temporal operator, which keeps online evaluation simple: one level of nesting, as agreed. Its semantics are exactly `within(MAX, MAX, φ)`, and with a predicate body `within(MAX, MAX, p)` and `always(p)` behave identically.
* `within`'s body stays a predicate.
* Parse errors are raised for:
  * a future `within` in an antecedent;
  * a past `within` in a consequent;
  * `within` on both sides.

### Semantics (implemented in `fcl/monitor.py`)

**Trace and anchor state.**
* `Monitor(formula, trace_length)`, then `start(state0)` once, then `step(state)` per adaptation step, then `finish()`.
* The trace is s₀, then s₁..s_k.
  * s₀ is virtual: the system before the first adaptation. It has the components and attributes of the simulation's initial state, and every ensemble present but **empty**.
  * s₁..s_k are one state per adaptation step, each including that step's proposed assignment.
* FCL computes `MAX = k − i` (remaining states) and `BEG = i` (states before the current one, a **positive** number) itself, where `k = trace_length` is the planned number of steps of the run.
  * This fixes `MAX` being off by one and ignoring the steps of the situation being run.
  * The past window `within(n, −t, p)` is truncated to `min(t, BEG)` states.
  * The paper currently defines `BEG = −i`. The code and `fcl/README.md` use `BEG = i` for now; if the paper is not changed, the code will be updated later.
* The top-level formula is evaluated only at s₀. A top-level `forall` therefore ranges over the initial components only, and a top-level predicate is checked at s₀ only.

**`always(φ)`.** φ is evaluated at every sᵢ, i ≥ 1. Sets inside it are re-evaluated in every state, so spawned components are covered.

**Future `within(n, t, p)`, created at sᵢ:**
* `n` and `t` are resolved at creation. A float `n` is rounded up (`ceil`), as in the paper's ⌈0.8·MAX⌉.
* Its effective window is sᵢ₊₁..s_{i+min(t,MAX)} (strict).
* It is resolved early: satisfied once `n` occurrences are reached, violated once the remaining window cannot reach `n`.
* `n ≤ 0` is immediately true. A window smaller than `n` is immediately violated, which is why `MAX > 0` guards are needed.

**End of the trace.** Only the regular end, after `trace_length` steps, is supported.

* `finish()` decides all pending obligations; their windows are then truncated by `MAX`, so every one is already resolved.
* **A premature end is intentionally not supported by the online monitor.** Examples are the Dragon dying at step 11 of the planned 30, or `finish()` being called early.
  * The reason: with a shorter trace, `MAX` would have been smaller, so some obligations would not have been created at all (e.g. `MAX > 0` in an antecedent), and their `n`/`t` would differ.
  * What happens instead: `finish()` drops all pending obligations without a verdict, and the limitation is documented in `fcl/README.md`.
  * Why that is enough for us: in our use cases a premature end means the Dragon was killed, i.e. the game was won.
* **Tests:** the regular end, including obligations created in the last states, is covered in `fcl/tests`, as is the documented behaviour of a premature end.

**Past `within(n, −t, p)`** counts `p` over the previous min(t, i) states, excluding sᵢ. History is kept per binding and starts at the first state where the binding was evaluated, so a spawned component gets a truncated window.

**Implication `a ⇒ c`.**
* An obligation for `c` is created **only when `a` holds** (fixes bug 1).
* A **new** obligation is created at every trigger. Obligations are keyed by (binding, trigger step) and kept in the monitor's pending list.
* Pending obligations are advanced every step regardless of the antecedent. Their violations are always reported (fixes bug 2).

**Predicate results** are converted with `bool()`. Today only a node result that `is False` counts as a violation (`ForAll`, `UserConstraint.check`).

* **Effect on existing constraints:** none. Predicates inside `within` are already converted with `bool()` in `TemporalObligation`, and no existing constraint has a bare predicate as the consequent or at the top level.
* **Why it is still worth doing:** the new grammar allows bare predicates in those places, e.g.

  ```
  forall f in `FieldComps`: `len(ProtectingEns[f])`
  ```

  This should fail for a field with no drones (the value 0). Today it would pass silently.

**Dropping obligations.** The `alive` parameter is renamed to `existing_objects: Collection | None` in `step()`. Obligations whose bindings contain an object that is not in `existing_objects` are discarded. This is needed, for example, for "after moving to the Cave, attack" when the warrior is killed in the Cave. Without it, that obligation would report a violation for a dead villager. `None` disables dropping.

### Simulator fixes found during exploration

1. **Lifecycle.** At the start of `run_simulation(steps)`, every `UserConstraint` is reset with `trace_length = steps`. Then `start()` is called with the pre-adaptation state: the simulation's current components, and the ensemble instances resolved with no members. At the end, `finish()` is called. This fixes constraint state leaking from one run into the next (a simulation instance can run several times, e.g. after the farm arrange step).
2. **Arrange runs do not evaluate constraints.** `random_assign_and_simulate` ([farm/simulation.py:105-112](farm/simulation.py#L105-L112)) sets a flag that skips `check_user_constraints`.
3. **Ensembles with the same group name.** `GoToCave` and `StayInCave` are both `"cave"` ([DSL/dragon.yaml:31,43](DSL/dragon.yaml#L31)), so the global `GoToCaveEn` also contains villagers who stay in the Cave.

   **Why we cannot simply resolve by ensemble instance:**
   * The AM only passes a **string**: `environment.assign_group(component, "cave")`. The simulation stores just that string (`self.assignments[component] = group_id`, [base_classes/simulation.py:153-162](base_classes/simulation.py#L153-L162)); no instance is ever chosen.
   * Group names are unique *within* one assignment method, but not *across* them: `"cave"` means `GoToCave` in `assign_in_village` and `StayInCave` in `assign_in_cave`.
   * `_resolve_ensembles` ([base_classes/simulation.py:230-236](base_classes/simulation.py#L230-L236)) receives the instances of *all* assignments for the global constraints. It matches members by `group_id == instance.name` only, so both instances named `"cave"` get every component assigned `"cave"`.
   * To know which instance a string refers to, we need the assignment method that was running when `assign_group` was called. The simulation already tracks it: `simulation.current_assignment` is set by `DSLAdaptation.adapt` ([base_classes/adaptation.py:30-39](base_classes/adaptation.py#L30-L39)) and used for error messages ([base_classes/simulation.py:166](base_classes/simulation.py#L166)).

   **Fix, chosen approach: store the assignment together with the group.**

   `self.assignments` becomes `dict[Component, AssignedGroup]`, where

   ```python
   class AssignedGroup(NamedTuple):
       assignment: str | None
       group_id: str
   ```

   * `assignment` is the assignment method, i.e. `simulation.current_assignment` at the time `assign_group` is called.
   * `_check_group` and `_assign_group` receive the assignment as a parameter.

   Files that change:

   * [base_classes/simulation.py](base_classes/simulation.py):
     * add the `AssignedGroup` type;
     * `assign_group` (l.153-162) stores `AssignedGroup(self.current_assignment, group_id)` and calls `self._check_group(component, group_id, self.current_assignment)`;
     * the abstract `_check_group`/`_assign_group` (l.170, 239) get the new signature `(component, group_id, assignment)`;
     * `_apply_assignments` (l.180-181) unpacks the pair;
     * `_resolve_ensembles` (l.230-236) matches `g.group_id == instance.name and (instance.assignment is None or g.assignment == instance.assignment)`.

     The `None` fallback keeps the non-DSL rule-based adaptations working. They call `assign_group` outside `DSLAdaptation.adapt`, so `current_assignment` is `None` for them.
   * [DSL/dsl_utils.py](DSL/dsl_utils.py):
     * `EnsembleInstance` (l.122-126) gets a field `assignment: str | None = None`;
     * `get_ensemble_instances_for_assignment` (l.95-118) receives the assignment name and sets it on each instance;
     * `load_ensemble_instances_for_assignment` (l.45-50) passes it on.

     `ResolvedEnsemble` ([base_classes/ensembles.py](base_classes/ensembles.py)) copies the instance's `__dict__`, so it needs no change.
   * [dragon/simulation.py](dragon/simulation.py):
     * the new signatures of `_check_group` (l.94) and `_assign_group` (l.121);
     * the spawn-member counting (l.109-110) reads `g.group_id`.

     With the assignment available, validation could use it instead of the villager's location, but the behaviour is kept as it is.
   * [farm/simulation.py](farm/simulation.py) (l.72, 92): the new signatures only.
   * [adaptations/jinja.py:153-154,199-200](adaptations/jinja.py#L153): only uses membership and `len`, so it is unaffected.
4. **Reporting repeated violations.** `UserConstraintError` gets `constraint_name` and `step`. In [test_generic.py](generated_adaptations/tests/test_generic.py) the functional tests group the violations by constraint name. Each constraint shows up to 3 distinct messages, followed by e.g. "(violated 17 times in total, at steps 4, 5, 6, …)", with the step list truncated.
5. `existing_objects` is passed as all components plus the beyond-control components.

### Rewriting the existing constraints to the new syntax

The meaning stays the same unless marked as a fix.

| File | Constraint | New form |
| --- | --- | --- |
| dragon | `all_warriors_should_go_to_cave` | `always(forall warrior in \`Warriors\`: \`warrior.location == Map.VILLAGE and MAX > 0\` implies within(1, MAX, \`warrior in GoToCaveEn\`))` (covers spawned warriors) |
| dragon | `all_farmers_should_stay_in_village` | `always(forall farmer in \`Farmers\`: \`farmer.location == Map.VILLAGE\`)` |
| dragon | `spawn_at_least_a_few_*` | `within(2, MAX, …)` |
| dragon | `attack_at_least_once_during_first_half` | `within(1, 15, …)` (unchanged) |
| dragon | `attack_after_moving_to_cave` | `always(forall warrior in \`Warriors\`: \`warrior in GoToCaveEn and MAX > 0\` implies within(1, MAX, \`warrior in AttackEn\`))` (**fix**: it can now fail) |
| dragon | `warriors_should_be_in_cave` | `within(\`0.8 * MAX\`, MAX, …)` |
| dragon | `game_is_won` | `within(1, MAX, \`DragonComps[0].hp <= 0\`)` |
| farm | `no_overprotect` | `forall field in \`FieldComps\`: always(…)` (the fields are fixed) |
| farm | `fully_protect_most_threatened` | `always(…)` |
| farm | `no_idle`, `consistency`, `closeness`, `coverage` | `within(\`k * MAX\`, MAX, …)` |

**Moving per-person constraints to the global section.** Constraints under an assignment only see that assignment's components: `VillagerComps` under `assign_in_village` holds only the villagers who are in the Village. So the per-person Dragon constraints move to the global `constraints:` section.

### Verification (Phase 2)

1. `pytest fcl/tests`: the former xfail bug tests pass. New tests cover:
   * strict future and past windows;
   * window truncation at the regular end of the trace, and the documented behaviour (dropping pending obligations) when the trace ends prematurely;
   * repeated triggers;
   * a false antecedent creating no obligation;
   * a top-level `forall` covering only the initial components, while `always(forall)` also covers new ones;
   * `existing_objects` dropping obligations;
   * `ceil` of `n`, and the cases `n = 0` and `t = 0`;
   * nested `forall`.
2. Take the snapshot `phase2/` (all mocks × {system, functional}) and `diff` it against `phase1/`.
   * **System tests:** identical output.
   * **Functional tests:** explain every difference. Expected: `attack_after_moving_to_cave` can now fail, the off-by-one at the window boundaries is fixed, and repeated messages are grouped.
3. Stop and report (no commit).

---

## Phase 3: Dragon Hunt, regular meals and Dragon regeneration

### Simulation (all parameters configurable; `0`/`null` disables a mechanic)

**[dragon/configs/default.yaml](dragon/configs/default.yaml), new keys:**

```yaml
meals:
  interval: 8            # a villager must eat at least once in every 8 consecutive steps
  cost: 1                # wheat per meal
  starvation_damage: 1   # HP lost per step once the interval is exceeded
dragon:
  Regeneration: 3        # HP regained per step without an attack (after the first attack)
```

**[dragon/simulation.py](dragon/simulation.py):**
* `"eat"` is added to `VALID_IN_VILLAGE`.
* `_check_group` adds `eaters × cost` to the existing wheat check for spawning ([dragon/simulation.py:94-119](dragon/simulation.py#L94-L119)), so meals and spawns share one budget.
* In `_assign_group`, `"eat"` sets the `EATING` state.
* `get_globals` additionally exposes `MEAL_INTERVAL` (the interval), so the constraints use the same value as the simulation.

**[dragon/components/villagers.py](dragon/components/villagers.py):**
* New state `VillagerState.EATING`.
* New counter `steps_since_meal`, starting at 0, and also 0 for newly spawned villagers.
* In `actuate`:
  * `EATING` subtracts `cost` from `farm.wheat` and resets the counter;
  * otherwise the counter is incremented;
  * if `counter ≥ interval`, the villager takes `get_attacked(starvation_damage)`.

**[dragon/components/dragon.py](dragon/components/dragon.py):**
* New class attribute `Regeneration` (configurable through the existing `set_config_values`) and a `fight_started` flag, set in `get_attacked`.
* In `actuate`, if the Dragon was not attacked and `fight_started`, then `hp = min(HP, hp + Regeneration)`.

**[dragon/plots.py:23](dragon/plots.py#L23)** adds `EATING` to the hard-coded list of states.

### ADSL ([DSL/dragon.yaml](DSL/dragon.yaml))

* A new ensemble `Eat` (`name: "eat"`, with a description of cost and interval) in `assign_in_village`.
* New Villager attribute `steps_since_meal` ("Steps since last meal").
* `fight_started` is **not** exposed in the ADSL. It is used only in the constraints; the AM can remember itself whether it has attacked.
* `domain_description` is updated.

### New Dragon constraint set ([DSL/dragon_constraints.yaml](DSL/dragon_constraints.yaml), all global)

* **Keep (in the Phase 2 form):**
  * `game_is_won`
  * `attack_at_least_once_during_first_half`
  * `all_warriors_should_go_to_cave`
  * `all_farmers_should_stay_in_village`
  * `spawn_at_least_a_few_warriors`
  * `attack_after_moving_to_cave`
* **Drop:** `warriors_should_be_in_cave` (80 %). It conflicts with the meals and is replaced by the no-gap constraint.
* **Decide after tuning:** `spawn_at_least_a_few_farmers`. It is kept unless the reference AM shows it conflicts with the wheat budget.
* **New: `eat_regularly`:**

  ```
  always(forall v in `VillagerComps`: `v.steps_since_meal >= MEAL_INTERVAL - 1` implies `v in EatEn`)
  ```

  Reason: "Villager {v} has not eaten for {v.steps_since_meal} steps and must eat now (step {step})." It uses the counter rather than a past window, so it matches the simulation exactly, including spawned villagers and the virtual s₀.
* **New: `keep_attacking`** (Dragon regeneration, past window):

  ```
  variables:
    gap: "len(AttackEn) == 0 and DragonComps[0].fight_started"
    MAX_GAP: "2"
  constraint: "always(within(`MAX_GAP`, `-MAX_GAP`, `gap`) implies `not gap`)"
  ```

  Reason: "The Dragon was not attacked for more than {MAX_GAP} steps in a row (step {step}), so it regenerated its health."
* **Optional, if we decide to include §B.7:** `pointless_trip`:

  ```
  always(forall w in `Warriors`: `w in GoToCaveEn` implies `w.steps_since_meal <= MEAL_INTERVAL - 4`)
  ```

  Where the bound comes from: the warrior is sent at step t and arrives in the Cave for t+1. It must be in the Village (eating) by the step where `steps_since_meal` reaches `interval − 1`, so it has to leave one step earlier. It can therefore attack at least once only if `steps_since_meal ≤ interval − 4` at step t. This is checked against the simulation during implementation. This is the "cannot check directly, but can refute" example.

### Situations

* Keep `seed=1..3` and `no_initial_warriors`.
* Add `hungry_villagers`: an arrange step that sets uneven `steps_since_meal` values, so that a fixed schedule from step 0 does not work.
* *(Added after Phase 2.)* Reconsider the trigger of `all_warriors_should_go_to_cave`. It currently reads `warrior.location == Map.VILLAGE and warrior not in GoToCaveEn and MAX > 0` (in the Village and not being sent right now). An alternative is "after a warrior returns to the Village (e.g. to eat), it goes back to the Cave" (trigger: `warrior in GoToVillageEn`), plus a second trigger for newly spawned warriors, who never return. Choose the form that reads better with the meals.

### Baselines (in `generated_adaptations/dragon/mock/`, descriptive names)

1. **`greedy_no_meals.py`**: the current `baseline.py`, renamed. All warriors attack, the farmers farm and spawn, and nobody ever eats. It is expected to fail `eat_regularly` and to lose villagers to starvation.
2. **`staggered_meals.py`**: a continuous attack with staggered meals. It:
   * spawns warriors early;
   * sends a warrior in the Cave home when `steps_since_meal ≥ interval − 2`, and lets at most half of the attacking warriors leave in the same step unless they are forced;
   * reserves wheat for the meals that are due before spawning;
   * sends a fed warrior straight back.
3. **`assemble_and_strike.py`** (your idea). It:
   * keeps the warriors in the Village and spawns new ones while they eat;
   * moves them to the Cave **all at the same time**, right after a meal;
   * lets them attack simultaneously until they must return (about `interval − 3` attack steps), so the Dragon is killed in one or two waves.

   Its interesting property: it may win quickly while breaking `keep_attacking` between the waves. That tells us whether the no-gap constraint is too strict compared with what "good" play looks like.

**Tuning.** I won't spend long iterating. I'll run each baseline over a few parameter variants (interval, `Regeneration`, `MAX_GAP`) and constraint variants (e.g. with or without `keep_attacking` or `spawn_at_least_a_few_farmers`). The test situations and the simulation runs for seeds 1–3 use the same `main.py` invocation as `generator.run_simulation` ([generated_adaptations/generator.py:246-258](generated_adaptations/generator.py#L246-L258)).

I'll then **report a table**, with one row per baseline × variant:

* functional and system test results per situation;
* the violated constraints;
* the win rate and the steps to win.

You decide the final parameters and constraints, and `DRAGON_GOOD_STEPS` ([generator.py:30](generated_adaptations/generator.py#L30)) is set to match.

### Prompts

* Update `dragon/configs/description2.yaml` (domain text with the new numbers) and [dragon/configs/strategy.yaml](dragon/configs/strategy.yaml) (strategy sentences that match every constraint).
* Regenerate the prompt with the README command ([generated_adaptations/README.md:15-21](generated_adaptations/README.md#L15-L21)). The generator writes to `generated_adaptations/prompts/<example><name>.md` and then calls `exit()`, so move the result into `generated_adaptations/prompts_user/` as `dragon_{strategy,requirements,both}.md`.
* Add the requirements section by hand, copied from the constraint reasons, as the README describes.
* The prompts are finalised only after the parameters and constraints are decided.

### Verification (Phase 3)

* `T(dragon, <baseline>, system|functional)` for every new baseline. The results go into the report table.
* Simulation runs for seeds 1–3: the win rate and steps per baseline, and a check of the plots (EATING appears, HP regeneration is visible).
* `pytest fcl/tests` still passes.
* The farm snapshot still matches `phase2/`, as a regression check.
* Stop and report with the table (no commit). The final parameters and constraints are set after your decision.

---

## Phase 4: Smart Farm, batteries and charging

### Simulation

* **[farm/simulation.py](farm/simulation.py):**
  * `_check_group`/`_assign_group` accept `"charging"`, which means `drone.assignTarget(self.charger)`.
  * Assigning a `TERMINATED` drone raises `InvalidAssignmentError("… ran out of battery …")`.
  * `get_globals` adds `Charger`.
  * A new config key `chargingRate`, which sets `Charger.ChargingRate`. The existing `charger:` key is the charger's location, so the rate cannot go there.
* **[farm/components/drone.py](farm/components/drone.py):**
  * `assignTarget` does nothing for a terminated drone, as a safety net against reviving it.
  * New property `battery_to_reach_charger` = `energyToFlyToCharger(includeSafetyMargin=False)`.
  * `protectsPoint` also excludes `CHARGING` drones.
* **[generated_adaptations/generator_utils.py](generated_adaptations/generator_utils.py):**
  * Remove `farm/configs/config_no_battery.yaml` from the farm configs. The file stays, so Level 0 can still be reproduced.
  * Add `Charger` to `reset_component_counters`.
* **[farm/configs/default.yaml](farm/configs/default.yaml):** add `chargingRate` (start at 0.02, then tune).

### ADSL ([DSL/drones.yaml](DSL/drones.yaml))

* `assign_drones` gets the components filter `if: "lambda component: component.state != DroneState.TERMINATED"`. Terminated drones are then neither passed to the AM nor required to be assigned.
* New ensemble `Charging` (`name: "charging"`).
* New Drone attributes `battery` and `battery_to_reach_charger`. The `state` description gains `charging`/`moving_to_charger`.
* New beyond-control component `charger` (`Charger`, singleton, `environment.charger`, attribute `location`).
* `domain_description` and `farm/configs/simulation_description_2.yaml` describe the battery, the consumption rates, the charger and the charging rate.

### New Smart Farm constraint set ([DSL/drones_constraints.yaml](DSL/drones_constraints.yaml))

* **Keep (in the Phase 2 form):** `no_overprotect`, `fully_protect_most_threatened`, `no_idle`, `consistency`, `coverage`.
* **Modify `closeness`:** the "closest drones" are taken only among drones that are not in `ChargingEn`. It may still conflict with proactive charging. If the charging baselines do not pass it, I propose dropping it.
* **New: `no_drone_runs_out`:**

  ```
  forall d in `environment.drones`: always(`d.state != DroneState.TERMINATED`)
  ```

  Drones are not spawned, so the top-level `forall` is enough.
* **New: `charge_when_low`:**

  ```
  always(forall d in `DroneComps`: `d.battery <= LOW_BATTERY and d not in ChargingEn and MAX > 0` implies within(1, 3, `d in ChargingEn`))
  ```

  `LOW_BATTERY` is a constants variable, e.g. 0.2.
* **New: `charging_not_interrupted`:**

  ```
  always(forall d in `DroneComps`: `d.state == DroneState.CHARGING and d.battery < 0.9` implies `d in ChargingEn`)
  ```

* **Fallback**, only if the reference AM cannot keep the most threatened field always fully protected: relax that constraint to "never under-protected for more than 5 steps in a row", using a past window.

### Situations

* Keep `seed=1`, which is the hard case with all drones fully charged.
* Keep `all_protecting` and `some_moving_drones`. With batteries, their arrange step now leaves the drones with partly used batteries.
  * *(Added after Phase 2.)* Make these two situations **longer** (e.g. 20–50 steps instead of `steps: 1`). Since Phase 2, `MAX` is the real run length, so in a 1-step run the "X % of the time" constraints (`consistency`, `closeness`, ...) must hold in the single step, which is not meaningful. Currently `protect_by_threat` fails `consistency` and `closeness` in these situations for this reason.
* Add `seed=2` with the full 300 steps, if the test runtime allows.

### Baselines

1. Run the existing mocks (`random_adapt`, `most_threatened`, `protect_by_threat`) and record what happens: the drones run out at about step 140.
2. Fix `most_threatened.py`, which builds `"protecting " + drone.target.id`; with the charger as a possible target that breaks. It should use only `Field` targets.
3. New baselines in `generated_adaptations/farm/mock/`:
   * **`reactive_charging.py`**:
     * the `protect_by_threat.py` logic;
     * a drone goes to charge only when its battery is low (≤ `LOW_BATTERY`);
     * charging is never interrupted.

     It is the "naive" strategy, expected to leave fields unprotected when all drones run low together.
   * **`proactive_charging.py`**: protect by threat with drones that have enough battery. In addition, drones below 0.7 battery are sent to charge early, but at most half of the drones charge at the same time. Low-battery drones always charge, and charging is never interrupted.
   * **`rotation_charging.py`**: a two-group rotation, generalising `RuleBasedProtectOneAdaptation` ([farm/adaptations/rule_based_smart.py:43-85](farm/adaptations/rule_based_smart.py#L43-L85)). One group protects while the other charges, and they swap when the protecting group runs low.
4. **Tuning**, as for the Dragon Hunt: a few variants of `chargingRate` and of the constraints (e.g. with or without `closeness`, and the relaxed most-threatened-field constraint).
   * The report table has the functional and system results and the violated constraints per baseline × variant.
   * It also shows the damage over seeds 1–3, compared with the no-battery numbers (`protect_by_threat` ≈ 60–76).
   * You decide the final parameters and constraints, and `FARM_GOOD_DAMAGE` ([generator.py:29](generated_adaptations/generator.py#L29)) is set to match.

### Prompts

* Update [farm/configs/strategy.yaml](farm/configs/strategy.yaml) with the charging strategy sentence.
* Regenerate the prompt and move it from `generated_adaptations/prompts/` to `generated_adaptations/prompts_user/farm_*.md`, then add the requirements by hand. As for the Dragon Hunt, this is finalised only after your decision.

### Verification (Phase 4)

* `T(farm, <baseline>, system|functional)` for every new and existing baseline. The results go into the report table.
* Simulation runs for seeds 1–3: the damage per baseline and the number of terminated drones.
* `pytest fcl/tests` and the dragon commands still pass, as a regression check.
* Stop and report with the table (no commit). The final parameters and constraints are set after your decision.

---

## Finishing up

* **Update the docs:**
  * [generated_adaptations/README.md](generated_adaptations/README.md) (the `--tb` mismatch, the new FCL package);
  * `fcl/README.md`;
  * [notes/harder-use-cases-plan.md](notes/harder-use-cases-plan.md), marking what was implemented and the final parameters.
* **Possible future work, not part of this plan:** fill in the numbers in the prompt descriptions from the config, which today are hand-written. Until then, the descriptions must be updated by hand when the parameters change.

## Critical files

* **New:**
  * `fcl/{__init__,parser,ast,monitor,utils}.py`, `fcl/grammar.lark`, `fcl/README.md`, `fcl/tests/`;
  * `generated_adaptations/dragon/mock/{staggered_meals,assemble_and_strike}.py`;
  * `generated_adaptations/farm/mock/{reactive_charging,proactive_charging,rotation_charging}.py`.
* **Renamed:** `generated_adaptations/dragon/mock/baseline.py` → `greedy_no_meals.py`.
* **Modified:**
  * FCL and constraints: `DSL/constraints/constraint.py`, `DSL/dsl_utils.py`, `utils.py`, `base_classes/simulation.py`;
  * tests: `generated_adaptations/tests/test_generic.py`, `generated_adaptations/tests/{dragon,farm}.py`, `generated_adaptations/generator_utils.py`, `generated_adaptations/generator.py`;
  * Dragon Hunt: `dragon/{simulation.py,components/villagers.py,components/dragon.py,plots.py,configs/*}`;
  * Smart Farm: `farm/{simulation.py,components/drone.py,configs/*}`;
  * DSL: `DSL/{dragon,drones}.yaml`, `DSL/{dragon,drones}_constraints.yaml`;
  * prompts: `generated_adaptations/prompts_user/*`;
  * baselines: `generated_adaptations/farm/mock/most_threatened.py`.
  * simulators, for the ensemble fix: `dragon/simulation.py`, `farm/simulation.py` (`_check_group`/`_assign_group` signatures), `DSL/dsl_utils.py` (`EnsembleInstance.assignment`).
* **Removed:** `DSL/constraints/{evaluation.py,parser.py,grammar.lark,grammar-simple.lark}` (moved or deleted).
