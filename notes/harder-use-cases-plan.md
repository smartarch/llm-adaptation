# Making the use cases harder for current LLMs: options and plan

*Status: brainstorming draft for team discussion. Nothing has been implemented yet.*

## 1. The problem

Newer models (GPT-6 Luna, DeepSeek V4 Flash, Claude Haiku 5.5, Qwen 3.8 Flash) usually produce a valid AM on the first attempt for both Dragon Hunt and Smart Farm, with every prompt variant. When that happens, the vibe-coding feedback loop never runs, so the results cannot show anything about RQ1 or RQ3.

What we want:

* With a strong model, the **first attempt should usually fail**. A rough target is a first-shot pass rate of at most 30–50 % with the "both" prompt, which gives the model the most help.
* The task should still be **solvable within a few iterations when the feedback includes generic and functional constraint violations**. If every variant fails, we again learn nothing about RQ3.
* **Changes to the simulation and the ADSL should stay small**, ideally reusing code that already exists.
* The use case should still be **easy to explain in the paper**: a few extra sentences in the domain description and 2–4 extra constraints.

## 2. What makes a task hard for a strong LLM on the first attempt

Looking at the generated code (e.g. [farm/all_strategy/gpt6luna_01/code_02.py](../generated_adaptations/farm/all_strategy/gpt6luna_01/code_02.py)), the current tasks reduce to a single greedy, stateless pass: sort by threat, take the closest drones, keep the drones that are already there. Strong models get this right immediately. They are much more likely to fail on the first attempt when the task has:

1. **Competing objectives that need a trade-off.** Two constraints pull in opposite directions, so a greedy rule that satisfies one breaks the other. Examples: protection vs. battery, regular meals vs. continuous attack.
2. **Bounded temporal obligations that repeat.** Rules of the form "after X happens, Y must happen within k steps", "at least once every k steps" or "never k steps in a row without Y". These force the AM to plan ahead and to keep state between adaptation steps. LLMs tend to write a stateless AM that recomputes everything at each step, and that breaks these constraints. This is also exactly what FCL is good at.
3. **Effects that depend on how actions combine or on their timing, and that the model is unlikely to simulate in its head.** Examples: an attack that only works with at least k attackers, the 3 steps a warrior is away from the Cave to eat, travel time to the charger, the order in which costs are paid within a step.
4. **Edge cases in the initial states.** States that a "typical case" AM does not handle, such as near-empty batteries or a single warrior.

Things we should **avoid**, because reviewers would see them as making the task artificially hard:

* Hiding information that is needed to solve the task, or making the prompt deliberately misleading. In particular, **the strategy (natural language) and the requirements (formalised constraints) must carry the same information**. The requirements only formalise the strategy and never add new rules. Every new constraint below therefore also needs one sentence in the strategy text.
* Arbitrary, hard-to-justify thresholds such as "coverage ≥ 0.93".

The difficulty should come from the domain itself. In each of the ideas below, the difficulty comes from a mechanism that makes sense in the domain.

A useful side effect: the new constraints can show **FCL features that the paper currently does not use in any experiment**, mainly past windows (`t < 0`). Right now the past-window example (Sec. 4.4.9) "was not used in the final experiments".

### 2.1 Which temporal patterns the current verifier supports

I checked [DSL/constraints/evaluation.py](../DSL/constraints/evaluation.py) and [parser.py](../DSL/constraints/parser.py). This matters for how the new constraints should be written:

* **A future window in the consequent creates only one obligation per binding for the whole run.** `TemporalWithin` keeps a single `TemporalObligation` per bound variable (`if bound_variables not in self.obligations`). That obligation is created the first time the formula is evaluated, not when the antecedent first holds, because `Implies.evaluate` always evaluates the right-hand side. So `∀w: (w ∈ GoToCave) ⇒ ◊¹_6 (w ∈ Attack)` works as "eventually, once", but **does not** re-arm every time the warrior goes to the Cave. Repeated "after X, Y within k" constraints would need a verifier extension: one obligation per (binding, trigger step), created only when the antecedent is true.
* **Past windows in the antecedent are already re-evaluated every step for each binding.** `TemporalHistory` keeps a rolling history per bound variable. A newly spawned component starts with an empty history, so it is not triggered too early.
* **Recommended pattern (works today): a "bounded streak" ban.** "Y happens at least once in every window of k steps", or equivalently "X never lasts k steps without Y", can be written as

  ```text
  forall v in `...`: consequent(k, `<bad condition for v>`) implies `False`
  ```

  This means "it is never the case that the bad condition held in each of the last k states". In the paper's notation it is `¬◊^k_{-k}(bad)`, up to whether the current state counts. The verifier currently includes the current state in the history window, which MT already flagged as inconsistent with the strict-window semantics in the paper. We should settle that before the new experiments, because these constraints depend on it.
* The grammar subset (`grammar-simple.lark`) has no `and`/`or` between temporal operators, but **conditions can be combined inside the Python expression**, e.g. `` `len(AttackEn) == 0 and DragonComps[0].hp < DragonComps[0].HP` ``.

Below, all constraint sketches that repeat are written in the bounded-streak form, so they need **no verifier changes**.

#### Bugs confirmed in the current implication handling

I confirmed these by running the real parser and evaluator on two short hand-made traces, using a temporary script outside the repository. The formula was `consequent(1, moved) implies once(attacked)`, the shape of `attack_after_moving_to_cave`.

1. **The consequent's obligation is created at the first evaluation, even if the antecedent is false.** `Implies.evaluate` evaluates the right-hand side first. As a result, an attack **before** moving to the Cave satisfies "attack after moving". *Trace:* attack at step 0, move at step 2, no attack afterwards → no violation.
2. **Violations are silently lost.** When the obligation resolves as violated at a step where the antecedent is false, `Implies` returns `True`. `check_end` then skips the obligation because it is already marked `resolved`. *Trace:* the warrior moves at step 1 and never attacks → **no violation reported**. So `attack_after_moving_to_cave` can currently never fail at the end of a run.
3. **Off-by-one at the end of the run.** An obligation created at step `s` with window `MAX` gets `end_step = s + MAX − 1`, so the last state is never checked. The window also includes the creation step (non-strict).
4. **Minor:** an obligation is not resolved early once it has `n` occurrences; it stays pending until the window ends.

These bugs affect the existing Dragon Hunt results (bug 2 hides real violations), so they should be fixed in any case.

#### How to re-arm implications: options

*Status: under discussion. The current view is that obligations should be re-armed and that windows must be strict in both directions.*

The question is how `ψ ⇒ ◊ⁿ_t φ` should create new obligations when `ψ` becomes true again, without creating a flood of obligations and without making `within` behave differently in different positions.

**(a) One obligation per binding; delete it when its window ends** (MT's proposal). The rule is the same everywhere: a new obligation can be created only after the previous window has ended.

* *Good:* windows of length `MAX` (`once`, `always`, `scattered`) naturally get exactly one obligation per run, or per component for a top-level `∀`.
* *Problem 1, implications can miss violations even with `n = 1`.* Example with `d.battery ≤ 0.2 ⇒ ◊¹_3 (d ∈ Charging)`: the battery is low at steps i and i+1, and the drone is in `Charging` only at i+1. Trigger i is then satisfied. Trigger i+1 needs `Charging` somewhere in i+2…i+4, but it is swallowed because i's window is still open. The drone can be pulled back to a field at i+2 without any violation.
* *Problem 2, top-level bounded windows change meaning.* `◊¹_15 (|Attack| ≥ 1)` is re-armed after step 15. It then also demands an attack in steps 16–30, so the constraint effectively becomes "an attack in every 15-step block". A re-arm at the last state has an empty window and fails.

**(b) One pending obligation per binding; delete it when resolved (satisfied or violated).** This is exact for implications with `n = 1`. The proof is below, and with `n > 1` the exact rule needs a small tweak. However, a top-level `once` would be re-armed as soon as it is satisfied, so this only works if top-level formulas are treated differently, which MT does not want.

**(c) Make "globally" explicit (recommended; this is MT's ◊^MAX_MAX idea applied consistently).**

* **Semantics:** every constraint is evaluated **once**, at its anchor state. That is the initial state, or, for a top-level `∀` over components, the state where the component first appears (keeping today's convention for spawned components). `within` behaves the same everywhere: one obligation per point where it is evaluated.
* **Repeating requirements are written explicitly** as `◊^MAX_MAX (ψ ⇒ ◊ⁿ_t φ)`, in the DSL `always(ψ implies within(n, t, φ))`. By the paper's own compositional semantics (Sec. 4.2), the inner `within` is evaluated at **every** state of the outer window. "Re-arm at every trigger" is therefore exactly what the formula means, not a special rule.
* **A plain `∀x ∈ S` is evaluated only at the initial state**, over the components present there. To cover components that appear later, the constraint must say so explicitly, using the set operators below.
* **Implementation:** support exactly one nesting shape, an outer `always` around an implication, and change the restriction in Sec. 5.2 from "no nesting" to "nesting only in this form". A new inner obligation is created at **every** step where `ψ` holds, which is exactly the formula's meaning. Obligations are advanced every step and deleted when resolved. There are at most `t` pending obligations per binding, so no optimisation is needed. If repeated violations of the same requirement make the feedback noisy, deduplicate identical messages in the report. A **bare** top-level implication is evaluated only at the initial state, like any other formula.

#### Entering and leaving sets: `S⁺` and `S⁻` (MT's proposal)

*Status: proposed by MT, analysed here.*

**Definition.** For a state-dependent set `S`, let `Sᵢ` be its value at state `sᵢ`, and set `S₋₁ = ∅`.

* `S⁺ᵢ = Sᵢ \ Sᵢ₋₁`: the elements that **entered** `S` at state i. With `S₋₁ = ∅`, `S⁺₀ = S₀`, so the initial members count as entering at s₀.
* `S⁻ᵢ = Sᵢ₋₁ \ Sᵢ`: the elements that **left** `S` at state i. This is empty at s₀.
* `∀x ∈ S⁺: φ` means: for every state i and every `x ∈ S⁺ᵢ`, `σ, i ⊨ φ[x]`. In other words, φ is anchored at each element's entry state. The same holds for `S⁻`.

This is syntactic sugar over the existing operators: `(∀x ∈ S: φ) ∧ ◊^MAX_MAX (∀x ∈ (S \ S_prev): φ)`, where `S_prev` is the value of `S` at the previous state. So "**constraints are evaluated at the initial state, and only temporal operators look at other states**" holds without exception.

**Should `S⁺` include the initial members? I recommend yes.**

* Almost all per-component constraints we need should apply to **all** components, initial and spawned ("every warrior goes to the Cave", "every villager eats regularly"). With the inclusive definition, each is one constraint. With the exclusive one, each has to appear twice, also in the paper.
* The definition stays uniform ("entered at state i, with `S₋₁ = ∅`") and symmetric with `S⁻` (nothing has left at s₀).
* "Only the initial components" is the plain `∀x ∈ S`. "Only components added later" is rare, and a guard such as `MAX < MAX₀` covers it, or the set difference if we ever implement it.

**`S⁺` doubles as an edge-triggered response.** "Entering S" works for any state-dependent set, not just component types: location sets, ensembles, attribute-defined sets. An element that leaves and re-enters triggers again. That is what we want for location and ensemble sets, and it cannot happen for type and role sets. Many "after X, do Y" requirements therefore become implication-free:

* `∀w ∈ InCave⁺: ◊¹_3 (w ∈ Attack)`: every time a villager arrives in the Cave, it attacks within 3 steps.
* `∀d ∈ Charging⁻: d.battery ≥ 0.9`: a drone leaves charging only when it is charged.

**Things to define:**

* **Obligations of a component that ceases to exist** (a villager dies, a drone is removed) are dropped. Otherwise they would fail on attribute and membership checks of a dead component. A constraint that is *about* removal uses `S⁻` explicitly.
* **Obligation keys** must include the anchor step, i.e. (binding, anchor step), not just the binding. An element can re-enter `S` while its previous obligation is still pending, and the same applies to level-triggered `always(ψ ⇒ ◊ⁿ_t φ)`.
* **Order within a step:** compute `S⁺` and `S⁻` by comparing with the previous step's set. Compare by component identity, not by equality.
* **The final state:** an element that enters `S` in the final state gets an empty future window. Constraints with a future window need the `MAX > 0` guard, e.g. `∀w ∈ Warriors⁺: MAX > 0 ⇒ ◊¹_MAX (w ∈ GoToCave)`. This is an implication evaluated once at the anchor state, so it needs no re-arming.

**Limitation: edge triggers can be fooled by oscillation.** Requirements of the form "never k steps in a row in a bad situation" should stay level-triggered. For example, take "the most threatened field is fully protected again within 5 steps", written with the edge trigger `∀f ∈ UnderprotectedMTF⁺: ◊¹_5 (f ∉ UnderprotectedMTF)`. If the most threatened field alternates between two fields every step, each obligation is satisfied by the field leaving the set, and nothing is ever protected. The level-triggered form `always(consequent(5, mtf_underprotected) implies False)` catches this.

**Implementation:** a new AST node, `ForAllEntered`/`ForAllLeft`, which stores the previous step's set per constraint. For each new element, it evaluates the body at that step and keeps the resulting obligations. A plain `ForAll` is evaluated only at the initial state. Set operations (`\`, `∪`) do not need to be in the implemented subset.

#### Do these constructs cover all the constraints we need?

The proposed subset is:

* `∀x ∈ S | S⁺ | S⁻: B`, where the body B is a predicate, `◊ⁿ_t p`, or `p ⇒ ◊ⁿ_t p`, evaluated once at the anchor state;
* a top-level `always(p ⇒ ◊ⁿ_t p)`, level-triggered;
* a top-level `always(◊ⁿ_{-t} p ⇒ p)`, a past window, for bounded streaks;
* plain top-level `◊ⁿ_t p`.

`p` is a state predicate, i.e. a Python expression.

| Constraint | Form | Covered? |
| --- | --- | --- |
| Game is won | `◊¹_MAX (dragon.hp ≤ 0)` | yes |
| Attack within the first 15 steps | `◊¹_15 (\|Attack\| ≥ 1)` | yes, one obligation |
| All warriors go to the Cave (incl. spawned) | `∀w ∈ Warriors⁺: MAX > 0 ⇒ ◊¹_MAX (w ∈ GoToCave)` | yes |
| All farmers stay in the Village | `∀f ∈ Farmers⁺: f.location = Village ∧ ◊^MAX_MAX (f.location = Village)`, or a predicate over all farmers inside one `◊^MAX_MAX` | yes; `always` should include the anchor state, see the note below |
| Spawn a few warriors / farmers | `◊³_MAX (\|SpawnWarrior\| ≥ 2)` | yes |
| Attack after moving to the Cave (every trip) | `∀w ∈ GoToCave⁺: MAX > 0 ⇒ ◊¹_MAX (w ∈ Attack)` | yes, edge-triggered |
| **D6** Eat at least every N steps | `∀v ∈ Villagers⁺: ◊¹_N (v ∈ Eat)` (first meal) + `∀v ∈ Eat⁻: ◊¹_N (v ∈ Eat)` (next meal after each meal) | yes. Use `Eat⁻`, not `Eat⁺`: with `Eat⁺`, a villager that eats in two consecutive steps would satisfy its obligation immediately and never be triggered again |
| **D7** Dragon not left unattacked 3 steps in a row | `always(◊³_{-3}(\|Attack\| = 0 ∧ hp < HP) ⇒ False)` | yes, level-triggered (global, no component) |
| Farm: no overprotection, most threatened field protected, no idle, consistency, closeness, coverage | top-level `◊^MAX_MAX` / `◊ⁿ_MAX` over the fixed fields | yes (fields and drones are not spawned) |
| **F1** No drone runs out of battery | `∀d ∈ Drones: ◊^MAX_MAX (d.state ≠ terminated)`, or, if terminated drones are removed, "`Drones⁻` is always empty" | yes |
| **F1** Low battery → charge within 3 steps | `∀d ∈ LowBattery⁺: ◊¹_3 (d ∈ Charging)` with `LowBattery = {d \| d.battery ≤ 0.2 ∧ d ∉ Charging}` | yes. Including `d ∉ Charging` in the set is essential: pulling the drone away from the charger makes it re-enter the set and re-triggers the obligation |
| **F1** Charging not interrupted | `∀d ∈ Charging⁻: d.battery ≥ 0.9` | yes |
| **F1** Most threatened field restored within 5 steps | `always(◊⁵_{-5}(mtf underprotected) ⇒ False)` | yes, level-triggered (see the oscillation limitation) |

**Note on `always` and the anchor state.** Because windows are strict, `◊^MAX_MAX φ` anchored at an element's entry state does not check φ in that state itself. The paper defines the inclusive variant `□φ ≜ φ ∧ ◊^MAX_MAX φ`, and the DSL's `always` should map to that inclusive variant. That is also what an architect would expect from "always".

**Migration:**

* Dragon `attack_after_moving_to_cave` becomes the `GoToCave⁺` form above.
* `all_warriors_should_go_to_cave` and `all_farmers_should_stay_in_village` switch to `Warriors⁺`/`Farmers⁺`. Their current variables, which are re-evaluated every step, behave like `S⁺` today.
* The farm constraints are unchanged.
* In the paper, Sec. 4.4.3, 4.4.4 and 4.4.7 are rewritten with `⁺`, which removes the informal "the constraint is evaluated as the system evolves".

---

## 3. Options for Smart Farm

### F1. Battery and charging (agreed)

**The change:** Drones consume battery and must fly to the charger to recharge. Most of this **is already implemented** in the simulation:

* [farm/components/drone.py](../farm/components/drone.py) has `battery`, energy consumption for moving and hovering, `TERMINATED` when the battery hits 0, `energyToFlyToCharger()` and the `MOVING_TO_CHARGER`/`CHARGING` states.
* [farm/components/charger.py](../farm/components/charger.py) charges the drones and automatically releases a drone when it is full.
* The generator currently switches batteries **off** through `farm/configs/config_no_battery.yaml`, see [generator_utils.py:13](../generated_adaptations/generator_utils.py#L13).
* The scenario is the original AFarCloud one, and earlier prompts already had a "charging" group (`farm/configs/unused/goal_charging.yaml`).

**Implementation effort (estimate: small, about half a day plus tuning):**

* Simulation: add a `"charging"` group to `_check_group`/`_assign_group` in [farm/simulation.py](../farm/simulation.py), which calls `drone.assignTarget(self.charger)`.
* Fix one problem: assigning a `TERMINATED` drone currently "revives" it, because `assignTarget` overwrites the state -> exclude terminated drones from `components` (or make `assignTarget` a no-op for them).
* ADSL ([DSL/drones.yaml](../DSL/drones.yaml)):
  * add a `Charging` ensemble;
  * add `battery` to the drone attributes;
  * add the `"charging"`/`"moving_to_charger"` values to `state`;
  * expose the charger as a beyond-control component (its `location`). Optionally expose a helper attribute such as `energy_to_charger`.
* Configuration: drop `config_no_battery.yaml` and tune `ChargingRate`. With the current values, hovering lasts about 140 steps and a full charge takes 100 steps, out of 300 steps in total. That is probably too slow to charge; a rate of around 0.02–0.03 may be needed so that the constraints can still be satisfied.

**Why this is hard on the first attempt:**

* It creates a real conflict with the existing "most threatened field always fully protected" constraint. The AM has to rotate drones and send a replacement **before** the protecting drone leaves to charge.
* The "re-assign explicitly every step" rule becomes a trap. A greedy AM pulls half-charged drones away from the charger and sends them back to a field.
* The safe threshold depends on the distance to the charger, so a fixed "battery < 25 %" rule is either wasteful or fatal.

**Constraint sketches** (FCL, with the DSL form where it matters; repeated obligations use the bounded-streak pattern from §2.1):

* *No drone runs out of battery:* `∀d ∈ Drones: ◊^MAX_MAX (d.state ≠ terminated)` (or "at most two drones run out of battery" if we want to allow a few failures).
* *A drone with low battery goes to charge soon* (never 3 steps in a row with low battery and not charging):

  ```text
  forall d in `DroneComps`: consequent(3, `d.battery <= 0.2 and d not in ChargingEn`) implies `False`
  ```

* *Charging is not interrupted:* `◊^MAX_MAX (∀d ∈ Drones: (d.state = charging ∧ d.battery < 0.9) ⇒ d ∈ Charging)`
* *No needless charging:* `◊^MAX_MAX (∀d ∈ Charging: d.state ∈ {charging, moving_to_charger} ∨ d.battery < 0.5)`
* *Handover / recovery*, which replaces the current "always" constraint: the most threatened field is fully protected in ≥ 90 % of the steps, and is never left without full protection for 5 steps in a row:

  ```text
  consequent(5, `len(ProtectingEns[most_threatened_field]) < most_threatened_field.drones_for_full_protection`) implies `False`
  ```

**Paper effort:** 2–3 sentences in the domain description ("Drones have a battery…, a charger at…"). This is easy to justify because it matches the real AFarCloud scenario more closely.

**Risks:**

* We need to tune the parameters so that the constraints can still be satisfied. We should write a reference AM that passes them (probably adapt from [`most_threatened.py`](/generated_adaptations/farm/mock/most_threatened.py) or [`protect_by_threat.py`](/generated_adaptations/farm/mock/protect_by_threat.py)).
* The `closeness` and `consistency` constraints may interact with charging and might need guards such as "drones that are not charging".

### F2. Minimum dwell time and anti-oscillation (constraints only, no simulation change)

**The change:** Add stateful functional constraints, for example:

* "a drone that starts protecting a field stays there for at least 10 steps, unless its battery is low or the field's threat drops to 0";
* "a drone is not reassigned more than twice in any 20-step window", which uses a past window.

**Effort:** only the DSL and the strategy text.

**Why this is hard:** The AM needs memory between steps (`self.*`), and LLMs usually write stateless AMs that re-sort the drones at every step. However, the GPT-6 Luna code already keeps the drones that are already on a field, so **on its own this is probably not enough**. It works best together with F1, where batteries and dwell time pull in opposite directions.

**Risk:** It can look arbitrary unless we motivate it, e.g. "each reassignment costs energy and time for the flight".

### F3. Heterogeneous drones or field priorities (lower value)

**The change:** Fields get a `crop_value` (the priority is threat × value), or there are two drone types with different speed and battery.

**Field values:** small effort, but LLMs handle a weighted sort easily. Low gain.

**Drone types:** more effort, because `protectionPlaces` depends on `Drone.Radius`, which is a class constant, and the effect on the constraints is unclear.

**Recommendation:** skip, or keep only as a stretch option.

### F4. Faster changes in bird behaviour (configuration only)

**The change:** Shift `birdFieldProbabilities` more often (e.g. every 30 steps instead of 100) and increase `birdCohesion`.

**Effect:** This puts more pressure on the handover and consistency constraints, and costs no code. It is useful as an **extra initial state** (see C1) rather than as a change on its own.

---

## 4. Options for Dragon Hunt (revised)

### 4.1 What the current game lacks

The current Dragon Hunt is easy for the same reason as the farm: every rule can be satisfied by one fixed, stateless rule per role. Warriors go to the Cave and attack forever, farmers farm and spawn whenever there is wheat. Nothing ever forces a component to **leave** its "steady state", and nothing couples the timing of one component to another.

To get the effects from §2, the extension should make the AM:

1. **track time per component**, e.g. "how long has this warrior been in the Cave";
2. **interrupt the steady state periodically**, so a warrior has to leave the Cave and come back;
3. **coordinate those interruptions**, so they do not all happen at the same time.

### D1. Automatic food upkeep (probably too easy)

**The change:** Every villager automatically eats 1 wheat per step. If there is not enough wheat, villagers lose HP.

**Assessment (agrees with the team's concern):** Because the upkeep is deducted automatically, it is just a lower net wheat production. The AM's only extra decision is "keep a reserve before spawning". Two farmers produce 10 wheat per step against an upkeep of 3–6, so starvation almost never happens anyway. It adds no per-component timing and no need to leave the Cave. **Not recommended on its own.** Its useful part (wheat is needed to keep villagers alive) is kept in D6, where eating is an explicit, periodic action.

#### D1.1. Food transport (alternative to D6)

**The change:** Wheat is produced in the Village, but warriors in the Cave can only eat food that has been carried there. Villagers that go from the Village to the Cave carry some wheat into a pantry in the Cave, and warriors eat from the pantry.

**Why this is hard:** It is a supply chain. Someone has to make periodic supply runs, so the "farmers always stay in the Village" constraint would have to be dropped, and the carriers are exposed to the Dragon. It is the same kind of difficulty as D6 (something must happen repeatedly but not every step), but the warriors can stay in the Cave.

**Effort:** larger than D6. It needs a new beyond-control component (the pantry), food carrying on arrival, an eating rule in the Cave, and probably a new ensemble in each assignment. Keep it as the alternative if D6 turns out to be too easy or awkward to explain.

### D2. The Dragon's shield: at least k attackers at once (difficulty knob)

**The change:** The Dragon only takes damage if at least 3 villagers attack in the same step. A weaker attack is blocked, but it still provokes the counterattack.

**Effort (estimate: tiny):** collect the attackers per step in `Dragon`, then apply the damage only if their count is ≥ 3. This is a few lines in [dragon/components/dragon.py](../dragon/components/dragon.py).

**Why this is hard:** The game starts with **1 warrior**, so the AM must first build up a group, which means spawning warriors early. Warriors must wait in the Cave (`StayInCave`) until there are enough of them. Combined with D6/D7, the rotation must also keep at least 3 attackers in the Cave at all times, which makes it a real scheduling problem.

**Constraint sketch:** *No wasted attacks:* `◊^MAX_MAX (|Attack| = 0 ∨ |Attack| ≥ 3)`

**Role in the plan:** On its own it is a static rule ("attack only when ≥ 3 are in the Cave") that strong models may get right. **Use it as a knob on top of D6 + D7** if the pilots are too easy.

### D3. Healing and retreat (alternative to D6, probably easier)

**The change:** A new Village ensemble `Heal`. Villagers in it regain 2 HP per step and cannot farm or spawn. Warriors with low HP should retreat.

**Effort (estimate: small):** one new ensemble and group in `VALID_IN_VILLAGE`, `_assign_group` and `Villager.actuate`; one ensemble in the ADSL.

**Assessment:** It also forces warriors to leave the Cave, but the trigger is the **current HP**, which can be observed directly. That makes it a reactive rule ("if hp ≤ 2, go home") that needs no memory and is easier than the time-based D6. HP loss is also random (the Dragon's counterattacks), so retreats are irregular and harder to verify reliably.

**Constraint sketches** (bounded-streak form):

* *An injured warrior retreats:* `forall w in Warriors: consequent(2, w.location == CAVE and w.hp <= 2 and w not in GoToVillageEn) implies False`
* *A healed warrior returns:* `forall w in Warriors: consequent(3, w.location == VILLAGE and w.hp == 6 and w not in GoToCaveEn) implies False`

### D4. Multi-step travel (not recommended as a first choice)

**The change:** Travelling between the Village and the Cave takes 2–3 steps.

**Effort:** small to medium. Villagers on the road are in neither assignment, so we would need either a third "travelling" set or to exclude them. The ADSL `if` conditions and the constraints that use `location` would also change.

**Effect:** It makes the timing harder, but it adds complexity mostly to the description, not to the decision. Note that D6 already gives warriors a 3-step absence (leave, eat, return) without any change to travel.

### D5. Dragon phases (sleeping / enraged)

**The change:** `dragon.state` cycles or switches at random. Attacking a sleeping Dragon gives no counterattack; an enraged Dragon hits twice as hard.

**Assessment:** It is a reactive rule ("if enraged, retreat") that strong models implement easily. **Lower value.**

### D6. Regular meals in the Village (recommended core)

This is the team's "warriors must come back periodically" idea, framed as eating.

**The change:**

* A new Village group `"eat"`. A villager assigned to it eats one meal, which costs 1 wheat. Like spawning, the assignment is rejected (a generic violation) if there is not enough wheat for all assigned villagers.
* Every villager must eat **at least once every N steps** (e.g. N = 8). Food exists only in the Village, so a warrior has to leave the Cave to eat.
* A villager that has not eaten for more than N steps starves and loses 1 HP per step. This gives the metrics-only feedback a signal too.
* Newly spawned villagers start fed.
* Optionally expose `steps_since_meal` as an attribute (see "Observability" below).

**Effort (estimate: small, about 20–30 lines):**

* [dragon/simulation.py](../dragon/simulation.py): `"eat"` in `VALID_IN_VILLAGE`, a wheat check in `_check_group` analogous to spawning, and a case in `_assign_group`.
* [dragon/components/villagers.py](../dragon/components/villagers.py): an `EATING` state, a `steps_since_meal` counter and the starvation damage.
* ADSL: one ensemble and one attribute. Domain description: 2 sentences. Strategy: 1 sentence.
* Behind a flag: `meal_interval: null` disables it, so Level 0 is unchanged.

**Why this is hard on the first attempt:**

* **Per-component timing.** The AM has to know how long each warrior has gone without food. It can read the attribute, or, if the attribute is not exposed, it must keep its own memory in `self.*` keyed by villager, including spawned and dead villagers.
* **Planning around travel.** A warrior that eats is away from the Cave for 3 steps: at step t it is assigned `"village"`, at t+1 `"eat"`, at t+2 `"cave"`, and it attacks again at t+3. It must therefore leave the Cave **2 steps before** its deadline. Off-by-one errors are very likely, and the feedback names the exact villager and step.
* **The wheat budget.** Meals compete with spawning for wheat. An AM that spawns first and feeds second will sometimes have no wheat left for a meal that is due.
* **Farmers have to eat too.** Each farmer gives up one farming step every N steps. That is easy, but it is one more thing a first attempt can forget.

**Constraint sketch** (works with today's verifier):

* *Every villager eats regularly:*

  ```text
  forall v in `VillagerComps`: consequent(8, `v not in EatEn`) implies `False`
  ```

  Reason: "Villager {v} has not eaten for 8 steps."

  In FCL notation: `∀v ∈ Villagers: ¬◊^8_{-8}(v ∉ Eat)`. This is the first experiment that uses a **past window**.

**Observability (decision for the team):** Exposing `steps_since_meal` is the most transparent option: no information is hidden, and the difficulty comes only from planning and coordination. Not exposing it is still fair, because the rule is fully stated in the prompt and the AM is a class that can keep state, but it adds a memory requirement. I suggest **exposing it** at first and keeping "hidden counter" as a difficulty knob.

### D7. The Dragon regenerates when left alone (recommended companion to D6)

D6 alone may still be easy: the AM can simply send every warrior to eat at the same time, accepting a few steps without attacks. D7 makes that costly and forces the AM to **stagger** the meals.

**The change:** Once it has been attacked for the first time, the Dragon regains R HP (e.g. R = 3) in every step in which it is not attacked.

**Effort (estimate: tiny):** about 3 lines in `Dragon.actuate` in [dragon/components/dragon.py](../dragon/components/dragon.py) (`got_attacked_this_step` already exists), plus 1 sentence in the description. Behind a flag (`dragon.Regeneration: 0`).

**Why this is hard:** The game starts with one warrior and spawned warriors arrive in batches, so warriors naturally get hungry **at the same time**. A greedy "go and eat when you have to" rule sends them all home together, and the Dragon regenerates. The AM has to:

* keep at least one warrior attacking while others eat, which means spawning a second warrior before the first one's first meal;
* or feed a warrior just before it goes to the Cave, so that the first meal is postponed.

This is a scheduling decision, not a reactive rule, and it is exactly the kind of thing the feedback can pinpoint ("not attacked for 3 steps in a row at step 14").

**Constraint sketch** (works with today's verifier; the HP condition switches the constraint on only after the first attack):

* *Keep up the pressure:*

  ```text
  consequent(3, `len(AttackEn) == 0 and DragonComps[0].hp < DragonComps[0].HP`) implies `False`
  ```

  Reason: "The Dragon was not attacked for 3 steps in a row (step {step}) and regenerated its health. Keep attacking it without longer breaks."

**Satisfiability check (rough):** With 1 warrior, every meal causes a 3-step gap, so the constraint forces a second warrior. Two farmers produce 10 wheat in the first step, which together with the initial 10 wheat pays for a warrior (12) in step 2. A second warrior is therefore achievable well before the first meal is due (N = 8). This needs to be confirmed with the reference AM.

### D8. Other ideas considered

* **Weapon durability** (repair in the Village after k attacks): it has the same structure as D6, but it is triggered by counting events rather than by time. It is harder to express in the implemented FCL subset (counting since the last repair), so D6 is preferred.
* **Cave capacity** (at most K villagers in the Cave): combined with D6 and D2, warriors would have to swap places exactly. It is a strong knob but risks becoming a puzzle. Keep it only as a last resort.
* **Spawn cooldown** (the Village can spawn only once every k steps): it adds little decision-making. Skip.

### 4.2 Proposed Dragon Hunt constraint set (Level 1)

The idea is to drop the constraints that conflict with the new mechanics or that become redundant.

| Constraint | Level 1 | Note |
| --- | --- | --- |
| Game is won | keep | |
| Dragon attacked within the first 15 steps | keep | Now interacts with the first meal and the second warrior |
| All warriors go to the Cave | keep | |
| All farmers stay in the Village | keep | Eating is in the Village, so there is no conflict (would be dropped with D1.1) |
| Spawn a few warriors / farmers | keep warriors, maybe drop farmers | Spawning warriors is now needed by D7 anyway |
| Warriors attack after moving to the Cave | keep | As is (once per warrior) |
| Warriors are mostly in the Cave (80 %) | **drop** | Conflicts with meals and is replaced by D7's no-gap constraint |
| Every villager eats every N steps (D6) | **new** | Per-component past window |
| Dragon not left alone for 3 steps (D7) | **new** | Global past window |
| No attacks with fewer than 3 villagers (D2) | knob | Only if too easy |

The strategy text gets the matching sentences, e.g.: "Every villager must eat in the Village at least once every 8 steps. Plan the warriors' meals so that the Dragon is never left without an attack for 3 steps in a row, because it regenerates."

---

## 5. Changes that apply to both use cases

### C1. Harder initial states (recommended in combination; cheap)

Extend `situations` in the ADSL and the `arrange` functions in [generated_adaptations/tests/](../generated_adaptations/tests/). Examples:

* **Farm:**
  * drones that start with low or random battery (with F1);
  * all drones far from the hot field;
  * fast-changing birds (F4).
* **Dragon:**
  * villagers who start hungry at different levels (with D6), so that the AM cannot rely on a fixed schedule from step 0;
  * low initial wheat (with D6), so that meals and spawning compete from the start;
  * warriors with low HP.

**Why it helps:** AMs written for the typical case often fail on these, and the feedback names the exact situation. This matches what the paper already argues in Sec. 5.5.2 about covering the possible runs, e.g. the "No Warriors" initial state.

**Risk:** Some constraints cannot be satisfied in degenerate states. We need to be careful when designing the initial states, and we should write a reference AM that passes all constraints on all initial states.

### C2. Make the strategy text less detailed (rejected)

**Rejected:** the strategy and the requirements must carry the same information (see §2), so we should not make the strategy vaguer than the constraints.

### C3. Tighten thresholds on existing constraints (cheap, not recommended)

Examples: coverage ≥ 0.9, closeness in 95 % of the steps, winning within 20 steps.

**Risks:** The thresholds look arbitrary, can easily become unsatisfiable, and make the task an optimisation problem rather than a specification-conformance one.

### C4. Larger scale (not recommended)

More fields and drones (the `farm/configs/scalability` configs exist). This hardly changes the logic the LLM has to get right; it mostly increases simulation time.

### C5. Underspecified parameters (not recommended)

For example, not stating the charging rate. It is realistic, but reviewers are likely to read it as making the task deliberately hard.

---

## 6. Comparison

| Option | Sim/ADSL effort | Expected first-attempt difficulty | Explanation cost in paper | Shows FCL features | Main risk |
| --- | --- | --- | --- | --- | --- |
| **F1** Battery & charging | Small (mostly exists) | **High** | Low (real AFarCloud feature) | Bounded streak, always, ≥ 90 % | Parameter tuning to keep the constraints satisfiable |
| F2 Dwell time | None (constraints only) | Low–medium alone, high with F1 | Low | Past windows, "at least k steps" | May look arbitrary |
| F3 Field values / drone types | Small / medium | Low | Low | – | Little gain |
| F4 Fast bird changes | Config only | Medium (with F1) | Very low | – | – |
| D1 Automatic upkeep | Tiny | Low | Very low | always | Just lower production |
| D1.1 Food transport | Medium | High | Medium | Bounded streak | More simulation and ADSL changes |
| D2 Shield (≥ 3 attackers) | Tiny | Medium alone, high with D6 + D7 | Very low | – | Could make D6 + D7 too hard |
| D3 Healing & retreat | Small | Medium (reactive) | Medium | Bounded streak | Random triggers |
| D4 Multi-step travel | Small–medium | Medium | Medium | – | Changes the assignment structure |
| D5 Dragon phases | Small | Low | Low | – | Too easy |
| **D6** Regular meals | Small | **Medium–high** | Low | **Past window per component** | Choice of N, whether to expose the counter |
| **D7** Dragon regeneration | Tiny | **High with D6** | Very low | **Past window, global** | Satisfiability with 1 initial warrior |
| **C1** Edge-case initial states | Tiny | Medium | Low | – | Degenerate states need guards |
| C2 Less detailed strategy | – | – | – | – | Rejected |
| C3 / C4 / C5 | None / config | Low–medium | – | – | See above |

---

## 7. Recommendation

1. **Smart Farm + Battery (F1)**, plus 1–2 initial states with low or uneven batteries (C1), and possibly F2's dwell-time constraint if pilots show it is still too easy.
2. **Dragon Hunt + Regular meals and Regeneration (D6 + D7)**, with the revised constraint set from §4.2 and 1–2 initial states with uneven hunger (C1). Difficulty knobs, in order: hide `steps_since_meal`, add the shield (D2). Alternative if D6 does not work well: food transport (D1.1).
3. **Frame it as a difficulty ladder in the paper:**
   * *Level 0* = the current use cases, run with the new models (only a few runs needed). Report that they solve them in one attempt. That is a finding, not a failure.
   * *Level 1* = the extended variants, which are the main experiments.

   This turns the reviewers' "try more LLMs" request into a stronger result: as the specification gets harder, even strong models need the loop, and the form of the feedback (RQ3) still matters.

Combined explanation cost in the paper: about 3–4 sentences of domain description and 2–4 new constraints per use case. The new constraints can replace weaker examples in Sec. 4.4: the unused "spawn every 10 steps" past-window example becomes the real "eat every 8 steps" constraint.

## 8. Pilot and calibration plan

1. **Implement the minimal versions of F1 and of D6 + D7** behind configuration flags (e.g. `meal_interval: null` and `dragon.Regeneration: 0` in `dragon/configs/default.yaml`), so that Level 0 stays reproducible. Put the new constraints in separate files (e.g. `DSL/drones_battery_constraints.yaml`, `DSL/dragon_meals_constraints.yaml`).
2. **Settle the window semantics in the verifier** (whether the current state is part of a past window, §2.1) before writing the final constraints, because the new constraints rely on past windows.
3. **Add more initial states (C1)**, but only add those that are solvable. Do not add too many new states, because that increases the simulation time. Also, do not include the degenerate states that cannot satisfy the constraints, e.g. fewer drones than the most threatened field needs, and fewer than two initial villagers (which prevents spawning new ones).
4. **Check that the constraints can be satisfied:** write a reference AM, by hand or vibe-coded with the strongest model and then checked by us, that passes all constraints on all initial states. This is also needed to argue that the constraints are aligned with the goals (Sec. 5.5.2).
5. **Pilot:** about 5 runs × 2 models (GPT-6 Luna and one cheaper model) with the "both" prompt and full feedback. Accept the variant if:
   * the first-attempt pass rate is ≤ ~50 %;
   * full feedback converges within ≤ 5–6 iterations in ≥ 80 % of the runs;
   * metrics-only feedback is noticeably worse.
6. **Adjust the difficulty:**
   * If it is too easy: Farm → F2; Dragon → hide `steps_since_meal`, then D2, or switch to D1.1.
   * If it is too hard: Farm → charging rate, the 90 % protection; Dragon → larger N, a longer allowed gap than 3, smaller regeneration, start with 2 warriors.
7. **Run the full experiments** with enough repetitions to answer reviewer R1: more runs per condition, plus success rate, median iterations and confidence intervals.

## 9. Open questions for the team

1. **Dragon Hunt:** do we prefer regular meals in the Village (D6) or food transport to the Cave (D1.1) as the core mechanic? Should `steps_since_meal` be visible to the AM?
2. **Verifier:** do we adopt (c) together with `S⁺`/`S⁻` (§2.1)? That is: constraints are evaluated at the initial state, repeating requirements use an explicit outer `always`, and new and re-entering components use `S⁺`, which I recommend should include the initial members. Independently of that, bugs 1–3 in §2.1 should be fixed, and the existing Dragon Hunt results may be affected by bug 2.
3. What is the compute and API budget per condition? A 300-step farm with batteries and more initial states makes each feedback iteration slower.
4. Would we accept the minimal extensions (F1, D6 + D7) even if the first-attempt pass rate stays around 50 %, or is the target lower?
