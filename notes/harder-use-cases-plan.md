# Making the use cases harder for current LLMs: options and plan

*Status: brainstorming draft for team discussion. Nothing has been implemented yet.*

## 1. The problem

Newer models (GPT-6 Luna, DeepSeek V4 Flash, Claude Haiku 5.5, Qwen 3.8 Flash) usually produce a valid AM on the first attempt for both Dragon Hunt and Smart Farm. When that happens, the vibe-coding feedback loop never runs, so the results cannot show anything about RQ1 or RQ3.

What we want:

* With a strong model, the **first attempt should usually fail**. A rough target is a first-shot pass rate of at most 30–50 % with the "both" prompt, which gives the model the most help.
* The task should still be **solvable within a few iterations when the feedback includes generic and functional constraint violations**. If every variant fails, we again learn nothing about RQ3.
* **Changes to the simulation and the ADSL should stay small**, ideally reusing code that already exists.
* The use case should still be **easy to explain in the paper**: a few extra sentences in the domain description and 2–4 extra constraints.

## 2. What makes a task hard for a strong LLM on the first attempt

Looking at the generated code (e.g. [farm/all_strategy/gpt6luna_01/code_02.py](../generated_adaptations/farm/all_strategy/gpt6luna_01/code_02.py)), the current tasks reduce to a single greedy, stateless pass: sort by threat, take the closest drones, keep the drones that are already there. Strong models get this right immediately. They are much more likely to fail on the first attempt when the task has:

1. **Competing objectives that need a trade-off.** Two constraints pull in opposite directions, so a greedy rule that satisfies one breaks the other. Examples: protection vs. battery, spawning vs. food.
2. **Bounded temporal obligations.** Rules of the form "after X happens, Y must happen within k steps", "stay at least k steps" or "never more than k steps without Y". These force the AM to plan ahead and to keep state between adaptation steps. LLMs tend to write a stateless AM that recomputes everything at each step, and that breaks these constraints. This is also exactly what FCL is good at.
3. **Effects that depend on how actions combine or on their timing, and that the model is unlikely to simulate in its head.** Examples: an attack that only works with at least k attackers, travel time to the charger, the order in which costs are paid within a step.
4. **Edge cases in the initial states.** States that a "typical case" AM does not handle, such as too few drones, no wheat, or near-empty batteries.

Two things we should **avoid**, because reviewers would see them as making the task artificially hard:

* Hiding information that is needed to solve the task, or making the prompt deliberately misleading.
* Arbitrary, hard-to-justify thresholds such as "coverage ≥ 0.93".

The difficulty should come from the domain itself. In each of the ideas below, the difficulty comes from a mechanism that makes sense in the domain.

A useful side effect: new constraints of types 2 and 3 can show **FCL features that the paper currently does not use in any experiment**: bounded response `◊¹_k` in the consequent, past windows (`t < 0`), and "at least k steps". Right now the past-window example (Sec. 4.4.9) "was not used in the final experiments".

---

## 3. Options for Smart Farm

### F1. Battery and charging (recommended)

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

**Constraint sketches** (FCL; all fit the implemented subset of one implication, `within` in the consequent and no nesting):

* *No drone runs out of battery:* `∀d ∈ Drones: ◊^MAX_MAX (d.state ≠ terminated)` (or "at most two drones run out of battery" if we want to allow a few failures).
* *A drone with low battery goes to charge soon:* `∀d ∈ Drones: (d.battery ≤ 0.2 ∧ d ∉ Charging ∧ MAX > 0) ⇒ ◊¹_3 (d ∈ Charging)`
* *Charging is not interrupted:* `◊^MAX_MAX (∀d ∈ Drones: (d.state = charging ∧ d.battery < 0.9) ⇒ d ∈ Charging)`
* *No needless charging:* `◊^MAX_MAX (∀d ∈ Charging: d.state ∈ {charging, moving_to_charger} ∨ d.battery < 0.5)`
* *Handover / recovery*, which replaces the current "always" constraint: the most threatened field is fully protected in ≥ 90 % of the steps, and when its full protection is lost it is restored within 5 steps: `¬full(mtf) ⇒ ◊¹_5 full(mtf)`.

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

## 4. Options for Dragon Hunt

### D1. Food upkeep (recommended)

**The change:** Every villager eats 1 wheat per step. If there is not enough wheat, every villager loses 1 HP (starvation).

**Effort (estimate: tiny, about 5–10 lines):** subtract the upkeep in `Farm.actuate` or `simulation_step` in [dragon/simulation.py](../dragon/simulation.py), plus 1 sentence in the domain description. Optionally expose `farm.upkeep` or `farm.starving` for the constraints.

**Why this is hard:** It turns the game into an economy. A farmer produces 5 wheat and eats 1; a warrior in the Cave produces nothing and eats 1. Several things now conflict: the "spawn at least a few" constraints, "all warriors in the Cave" and winning in 30 steps. LLMs tend to spawn greedily, and a greedy AM starves. Getting this right requires reasoning about the order of payments within a step (spawn cost vs. upkeep) and keeping a reserve.

**Constraint sketches:**

* *Villagers never starve:* `◊^MAX_MAX (Farm.wheat ≥ |Villagers|)`. The exact form depends on when the upkeep is paid.
* The existing constraints stay and now conflict, e.g. spawning vs. reserve.

**Paper effort:** 1 sentence plus 1 constraint, and it is intuitive ("villagers need to eat").

#### D1.1. Food transport (if D1 is too easy)

**To make it even harder:** We could also require that the wheat is transported to the Cave so that villagers there can eat it. This is motivated by the fact that the wheat is produced in the Village, so the warriors in the Cave cannot eat it unless it is carried there. However, this is a bigger change to the simulation and the ADSL, so we should try the simpler version first.

### D2. The Dragon's shield: at least k attackers at once (recommended)

**The change:** The Dragon only takes damage if at least 3 villagers attack in the same step. A weaker attack is blocked, but it still provokes the counterattack.

**Effort (estimate: tiny):** collect the attackers per step in `Dragon`, then apply the damage only if their count is ≥ 3. This is a few lines in [dragon/components/dragon.py](../dragon/components/dragon.py).

**Why this is hard:**

* The game starts with **1 warrior**, so the AM must first build up a group. That means spawning warriors early, which ties into D1's economy.
* Warriors must wait in the Cave (`StayInCave`) until there are enough of them. This conflicts with the existing "attack after moving to the Cave" constraint, which we would turn into a bounded version: "after moving to the Cave, attack within 5 steps".
* The "attack in the first 15 steps" deadline becomes a real planning problem.

**Constraint sketches:**

* *No wasted attacks:* `◊^MAX_MAX (|Attack| = 0 ∨ |Attack| ≥ 3)`
* *Warriors do not wait forever:* `∀w ∈ Warriors: (w ∈ GoToCave ∧ MAX > 0) ⇒ ◊¹_6 (w ∈ Attack)`
* The existing `◊¹_15 (|Attack| ≥ 1)` now implies building up the group early.

**Paper effort:** 1 sentence ("the Dragon's scales can only be pierced by a coordinated attack of at least three villagers").

### D3. Healing and retreat (optional, if D1 + D2 are not enough)

**The change:** A new Village ensemble `Heal`. Villagers in it regain 2 HP per step and cannot farm or spawn. Warriors with low HP should retreat.

**Effort (estimate: small):** one new ensemble and group in `VALID_IN_VILLAGE`, `_assign_group` and `Villager.actuate`; one ensemble in the ADSL.

**Why this is hard:** It adds two-way trips with temporal obligations, and it conflicts with "warriors mostly in the Cave" (which may need relaxing to 60 %) and with the shield (D2), because pulling a warrior back can drop the group below 3.

**Constraint sketches:**

* *An injured warrior retreats:* `∀w ∈ Warriors: (w.location = Cave ∧ w.hp ≤ 2) ⇒ ◊¹_2 (w ∈ GoToVillage)`
* *A healed warrior returns:* `∀w ∈ Warriors: (w.location = Village ∧ w.hp = 6 ∧ MAX > 0) ⇒ ◊¹_3 (w ∈ GoToCave)`
* *Healing is not interrupted*, using a past window: `(◊¹_{-1} w ∈ Heal ∧ w.hp < 6) ⇒ w ∈ Heal`

**Paper effort:** moderate, about 2 sentences and 2–3 constraints. This is the richest showcase of FCL's temporal features.

### D4. Multi-step travel (not recommended as a first choice)

**The change:** Travelling between the Village and the Cave takes 2–3 steps.

**Effort:** small to medium. Villagers on the road are in neither assignment, so we would need either a third "travelling" set or to exclude them. The ADSL `if` conditions and the constraints that use `location` would also change.

**Effect:** It makes the timing harder (the 15-step deadline, the shield), but it adds complexity mostly to the description, not to the decision.

### D5. Dragon phases (sleeping / enraged), as an alternative to D2

**The change:** `dragon.state` cycles or switches at random. Attacking a sleeping Dragon gives no counterattack; an enraged Dragon hits twice as hard.

**Assessment:** It is a reactive rule ("if enraged, retreat") that strong models implement easily. **Lower value** than D2.

---

## 5. Changes that apply to both use cases

### C1. Harder initial states (recommended in combination; cheap)

Extend `situations` in the ADSL and the `arrange` functions in [generated_adaptations/tests/](../generated_adaptations/tests/). Examples:

* **Farm:**
  * drones that start with low or random battery (with F1);
  * fewer drones than the most threatened field needs;
  * all drones far from the hot field;
  * fast-changing birds (F4).
* **Dragon:**
  * 0 wheat;
  * exactly 1 farmer (cannot spawn alone, since spawning needs 2 villagers);
  * warriors with low HP;
  * many villagers and little wheat (with D1).

**Why it helps:** AMs written for the typical case often fail on these, and the feedback names the exact situation. This matches what the paper already argues in Sec. 5.5.2 about covering the possible runs, e.g. the "No Warriors" initial state.

**Risk:** Some constraints cannot be satisfied in degenerate states. They need guards such as "if at least 2 villagers…", or we need to drop the state.

### C2. Make the strategy text less detailed (cheap, but needs careful framing)

The last commits ("Update strategies to cover all constraints") made the strategy text almost a word-for-word restatement of the constraints. With a strategy that describes only the intent, without the thresholds, the "strategy only" prompt variant becomes meaningfully harder.

**Benefit:** This is the realistic setting: the domain expert states the intent, and the formal constraints are used for verification.

**Risk:** A first-attempt failure can then be explained simply as "the information was missing". It does not help the "both" or "requirements" variants. **Use it as an additional lever, not as the main fix.**

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
| **F1** Battery & charging | Small (mostly exists) | **High** | Low (real AFarCloud feature) | Bounded response, always, ≥ 90 % | Parameter tuning to keep the constraints satisfiable |
| F2 Dwell time | None (constraints only) | Low–medium alone, high with F1 | Low | Past windows, "at least k steps" | May look arbitrary |
| F3 Field values / drone types | Small / medium | Low | Low | – | Little gain |
| F4 Fast bird changes | Config only | Medium (with F1) | Very low | – | – |
| **D1** Food upkeep | Tiny | **Medium–high** | Very low | always | Must keep the game winnable in 30 steps |
| **D2** Shield (≥ 3 attackers) | Tiny | **Medium–high** | Very low | Bounded response | Interaction with the 15-step constraint |
| D3 Healing & retreat | Small | High | Medium | Bounded response, past window | Larger constraint set |
| D4 Multi-step travel | Small–medium | Medium | Medium | – | Changes the assignment structure |
| D5 Dragon phases | Small | Low | Low | – | Too easy |
| **C1** Edge-case initial states | Tiny | Medium | Low | – | Degenerate states need guards |
| C2 Less detailed strategy | None | Medium (strategy-only prompt) | None | – | "Unfair" critique |
| C3 / C4 / C5 | None / config | Low–medium | – | – | See above |

---

## 7. Recommendation

1. **Smart Farm + Battery (F1)**, plus 1–2 initial states with low or uneven batteries (C1), and possibly F2's dwell-time constraint if pilots show it is still too easy.
2. **Dragon Hunt + Economy and Shield (D1 + D2)**, plus edge-case initial states (C1: no wheat, a single farmer). Keep D3 (healing) in reserve as the next step up if the pilots are still too easy.
3. **Frame it as a difficulty ladder in the paper** instead of quietly replacing the use cases:
   * *Level 0* = the current use cases. Report that newer models solve them in one attempt. That is a finding, not a failure.
   * *Level 1* = the extended variants.

   This turns the reviewers' "try more LLMs" request into a stronger result: as the specification gets harder, even strong models need the loop, and the form of the feedback (RQ3) still matters. It also allows a cost argument, e.g. "a small model plus the feedback loop vs. a large model in one attempt".

Combined explanation cost in the paper: about 3–4 sentences of domain description and 3–5 constraints per use case. Some of these constraints can replace weaker examples in Sec. 4.4, e.g. the unused "spawn every 10 steps".

## 8. Pilot and calibration plan

1. **Implement the minimal version of F1 and of D1 + D2** behind configuration flags (e.g., make the wheat consumption a constant that is set to 0 in the `dragon/configs/default.yaml` config), so that Level 0 stays reproducible. Put the new constraints in separate files (e.g. `DSL/drones_battery_constraints.yaml`).
2. **Add more initial states (C1)**, but only add those that are solvable. Do not add too many new states becuase that increases the simulation time. Also, do not include the degenerate states that cannot satisfy the constraints, e.g. fewer drones than the most threatened field needs, and less than two initial villagers (which prevents spawning new ones).
3. **Check that the constraints can be satisfied:** write a reference AM, by hand or vibe-coded with the strongest model and then checked by us, that passes all constraints on all initial states. This is also needed to argue that the constraints are aligned with the goals (Sec. 5.5.2).
4. **Pilot:** about 5 runs × 2 models (GPT-6 Luna and one cheaper model) with the "both" prompt and full feedback. Accept the variant if:
   * the first-attempt pass rate is ≤ ~50 %;
   * full feedback converges within ≤ 5–6 iterations in ≥ 80 % of the runs;
   * metrics-only feedback is noticeably worse.
5. **Adjust the difficulty:**
   * If it is too easy, consider F2 (Farm) and D1.1 or D3 (Dragon).
   * If it is too hard, relax the thresholds (charging rate, shield size 3 → 2, the 90 % protection).
6. **Run the full experiments** with enough repetitions to answer reviewer R1: more runs per condition, plus success rate, median iterations and confidence intervals.

## 9. Open questions for the team

1. Which prompt variants do the new models currently pass on the first attempt: `strategy`, `requirements`, `both`, or all of them? If even `strategy` passes, C2 is worth doing as well.
2. Do we **add** the harder variants as Level 1, as I recommend, or **replace** the current use cases? Replacing would also require re-running the GPT-5 nano results.
3. What is the compute and API budget per condition? A 300-step farm with batteries and more initial states makes each feedback iteration slower.
4. Was the battery/charging variant part of the setup in [40]? If so, we can reuse its domain-description text and cite it.
5. Would we accept a single extension per use case (F1, and D1 + D2) even if the first-attempt pass rate stays around 50 %, or is the target lower?
