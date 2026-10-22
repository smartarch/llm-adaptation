# Making the use cases harder for current LLMs

*Status: proposal for team agreement. Nothing has been implemented yet.*

Part I is the executive summary we need to agree on. Part II contains the detailed analysis and the backup options in case we reject part of the proposal.

---

# Part I: Executive summary

## 1. Problem and goal

**Problem.** Newer models (GPT-6 Luna, DeepSeek V4 Flash, Claude Haiku 5.5, Qwen 3.8 Flash) usually produce a valid adaptation manager (AM) on the **first attempt** for both use cases, with every prompt variant. The vibe-coding feedback loop never runs, so the experiments say nothing about RQ1 and RQ3.

**Goal.** Make both use cases harder in a way that comes from the domain, not from hiding information:

* With a strong model, the first attempt should usually fail (target: ≤ 30–50 % first-attempt pass rate).
* With generic and functional constraint violations as feedback, a valid AM should be found within a few iterations.
* The changes to the simulation and the ADSL stay small, and the use cases stay easy to explain in the paper.
* The strategy (natural language) and the requirements (constraints) keep carrying the **same information**. Every new constraint gets a matching sentence in the strategy.

**What makes a task hard for a strong LLM.** The current tasks can be solved by one greedy, stateless rule per step. Strong models fail on the first attempt when the AM has to:

* **plan ahead** and keep state between steps;
* **resolve conflicting goals**;
* **coordinate components in time**, so that they do not all do the same thing at once.

Both proposed extensions add exactly that, and both are naturally expressed with FCL's bounded windows.

## 2. Proposal at a glance

| Area | Proposal | Key difficulty for the AM |
| --- | --- | --- |
| **Smart Farm** | Drone batteries and charging (simple charger, any number of drones charging at once) | All drones start fully charged and run out at about the same time. Reactive "charge when low" leaves the fields unprotected, so the AM has to **stagger and pre-charge** drones. |
| **Dragon Hunt** | Regular meals in the Village, combined with Dragon regeneration | Warriors must leave the Cave periodically to eat, but the Dragon must not be left alone. The AM has to **stagger the meals** and plan around the 3 steps a warrior is away. |
| **FCL / verifier** | Explicit "globally" ($\square$), strict windows, bug fixes | Gives consistent semantics for repeating constraints and for spawned components. Also needed to state the new constraints. |
| **Paper** | "Difficulty ladder": Level 0 = current use cases, Level 1 = extended ones | We report that new models solve Level 0 in one attempt, which is a finding, and use Level 1 for the main experiments. |

All simulation changes go behind configuration flags, so that Level 0 stays reproducible.

## 3. Smart Farm: batteries and charging

**Mechanics.** Drones consume battery while flying and hovering (this already exists in [drone.py](../farm/components/drone.py)). A new group `"charging"` sends a drone to the charger, which charges any number of drones at once and releases a drone when it is full (this already exists in [charger.py](../farm/components/charger.py)). A drone with an empty battery is out of the game.

**Implementation effort (small).**

* Simulation: add the `"charging"` group in [farm/simulation.py](../farm/simulation.py). Make sure a terminated drone cannot be revived by an assignment; today `assignTarget` would overwrite its state.
* ADSL: add the `Charging` ensemble, the drone attribute `battery`, the new `state` values, and the charger location.
* Configuration: drop `config_no_battery.yaml` from [generator_utils.py](../generated_adaptations/generator_utils.py#L13) and tune `ChargingRate`.

**Why it is hard.** With the current parameters, a hovering drone lasts about 140 steps of a 300-step run. All drones start fully charged and are deployed together, so they all run low at about the same time. A first-attempt AM typically sends a drone to charge when its battery is low. That sends many drones away at once, and the most threatened field stays unprotected for a long time. A good AM must:

* rotate drones;
* **pre-charge drones that are not currently needed**, so that charged replacements are available later;
* never pull a drone away from the charger before it is charged.

The **default initial state (all drones full)** is therefore the hard state; states with low batteries are comparatively easy.

**Example constraints** (FCL notation; $\square$ and strict windows as defined in §5):

* *No drone runs out of battery:* $\forall d \in \mathit{Drones}: \square\, (d.\mathit{state} \neq \mathit{terminated})$
* *A drone that runs low goes to charge within 3 steps:* $\square\, (\forall d \in \mathit{Drones}: d.\mathit{battery} \le 0.2 \wedge d \notin \mathit{Charging} \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging}))$. A new obligation is created in every step in which the condition holds. Pulling a drone away from the charger therefore triggers the constraint again.
* *Charging is not interrupted:* $\square\, (\forall d \in \mathit{Drones}: d.\mathit{state} = \mathit{charging} \wedge d.\mathit{battery} < 0.9 \Rightarrow d \in \mathit{Charging})$ (a drone leaves the charger only when charged).
* The existing constraints stay, **including "the most threatened field is always fully protected"**. It should still be satisfiable with batteries: the largest field needs about half of the drones, so the AM can alternate two groups and charge one while the other protects. This makes the constraint a strong driver of the pre-charging behaviour. If the hand-written reference AM cannot satisfy it, we relax it to *"never unprotected for more than 5 steps in a row"*: $\square\, (\lozenge^{5}_{-5}\, \mathit{under}(\mathit{mtf}) \Rightarrow \neg \mathit{under}(\mathit{mtf}))$.
* The `closeness` constraint should only consider drones that are not charging.

**Strategy sentence (example):** "Drones have limited battery and must recharge at the charger. Do not let all drones run out at the same time: charge unused drones in advance, send a drone to charge as soon as its battery is low, and never interrupt charging."

## 4. Dragon Hunt: regular meals and Dragon regeneration

**Mechanics.**

* A new Village group `"eat"`. A meal costs 1 wheat; like spawning, the assignment is rejected if there is not enough wheat.
* Every villager must eat **at least once every $N$ steps** (e.g. $N = 8$). Food is only in the Village, so a warrior has to leave the Cave to eat. A villager that has not eaten for longer starves and loses 1 HP per step. Spawned villagers start fed.
* **Dragon regeneration:** after its first attack, the Dragon regains $R$ HP (e.g. $R = 3$) in every step in which nobody attacks it.

**Implementation effort (small).** About 20–30 lines:

* [dragon/simulation.py](../dragon/simulation.py): the `"eat"` group and its wheat check.
* [villagers.py](../dragon/components/villagers.py): an `EATING` state, a `steps_since_meal` counter and starvation.
* [dragon.py](../dragon/components/dragon.py): about 3 lines for regeneration.
* ADSL: one ensemble and one attribute.

**Why it is hard.** A warrior that eats is away from the Cave for 3 steps: it leaves, eats, and returns. It therefore has to leave **before** its deadline, which invites off-by-one errors. All warriors start or spawn at about the same time, so they get hungry together. A greedy "eat when you must" rule sends them all home at once, and the Dragon regenerates. A good AM must:

* stagger the meals;
* get a second warrior early (one warrior alone cannot eat without leaving the Dragon unattacked);
* reserve wheat for meals that are due, instead of spending it all on spawning.

**Example constraints:**

* *Every villager eats regularly:* $\square\, (\forall v \in \mathit{Villagers}: \lozenge^{8}_{-8}\, (v \notin \mathit{Eat}) \Rightarrow v \in \mathit{Eat})$, i.e. "a villager who did not eat in any of the previous 8 steps must eat now". This is the first experiment that uses a **past window**. Spawned villagers are covered, because the set is re-evaluated in every state inside $\square$.
* *The Dragon is never left unattacked for 3 steps in a row (once the fight has started):* $\square\, (\lozenge^{2}_{-2}\, \mathit{gap} \Rightarrow \neg \mathit{gap})$, where $\mathit{gap} \equiv \lvert \mathit{Attack} \rvert = 0 \wedge \mathit{dragon}.\mathit{hp} < \mathit{dragon}.\mathit{maxHp}$.
* *All warriors go to the Cave, including spawned ones (and warriors that came back to eat):* $\square\, (\forall w \in \mathit{Warriors}: w.\mathit{location} = \mathit{Village} \wedge \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave}))$.
* *Every time a warrior goes to the Cave, it attacks afterwards:* $\square\, (\forall w \in \mathit{Warriors}: w \in \mathit{GoToCave} \wedge \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{Attack}))$. Membership in $\mathit{GoToCave}$ lasts one step, so this triggers once per trip.

**Changes to the existing constraint set.**

* Drop "warriors are mostly in the Cave (80 %)", which conflicts with meals and is replaced by the no-gap constraint.
* Possibly drop "spawn a few farmers".
* Keep the rest (game won, attack in the first 15 steps, warriors go to the Cave, farmers stay in the Village, spawn warriors, attack after moving). Details are in §B.4.

**Strategy sentence (example):** "Every villager must eat in the Village at least once every 8 steps. Plan the warriors' meals so that the Dragon is never left unattacked for 3 steps in a row, because it regenerates."

**Difficulty knobs, if the pilots show it is too easy:**

1. hide `steps_since_meal`, so the AM must keep its own record;
2. the Dragon's shield: damage only if at least 3 villagers attack at once.

## 5. FCL semantics and verifier

**Semantics we propose to adopt.**

1. **A constraint is evaluated in the initial state.** Only temporal operators look at other states. Inside a temporal operator, component and ensemble sets are re-evaluated in every state, as already described in Sec. 4.2 of the paper.
2. **Repeating requirements use an explicit "globally"**: $\square\varphi \triangleq \varphi \wedge \lozenge^{\mathit{MAX}}_{\mathit{MAX}}\varphi$, which includes the current state. By the compositional semantics, an inner $\lozenge^{n}_{t}$ is evaluated in every state, so a new obligation is created at every step where the antecedent holds.
3. **Spawned components are covered by putting the $\forall$ inside $\square$.** $\square\, (\forall w \in \mathit{Warriors}: \ldots)$ re-evaluates the set in every state, so it includes spawned warriors. A plain top-level $\forall w \in \mathit{Warriors}$ covers only the initial components. "Once from the moment the component appears" is expressed by a state condition in the antecedent, e.g. "while the warrior is in the Village".
4. **All windows are strict** (the current state is excluded) in both directions.

**Examples showing the difference:**

* $\lozenge^{1}_{15}\, (\lvert \mathit{Attack} \rvert \ge 1)$: one obligation for the first 15 steps; it is not repeated.
* $\forall w \in \mathit{Warriors}: \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave})$: one obligation per **initial** warrior; spawned warriors are not covered.
* $\square\, (\forall w \in \mathit{Warriors}: w.\mathit{location} = \mathit{Village} \wedge \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave}))$: covers all warriors, including spawned ones; a new obligation in every step a warrior is in the Village.
* $\square\, (\forall d \in \mathit{Drones}: d.\mathit{battery} \le 0.2 \wedge d \notin \mathit{Charging} \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging}))$: a new obligation in every step where the condition holds.

**Implemented subset** (enough for all planned constraints; the coverage check is in §B.2):

* $[\forall x \in S:]\ B$ with $B \in \{p,\ \lozenge^{n}_{t} p,\ p \Rightarrow \lozenge^{n}_{t} p\}$: evaluated once, in the initial state.
* $\square\, ([\forall x \in S:]\ R)$ with $R \in \{p,\ p \Rightarrow \lozenge^{n}_{t} p,\ \lozenge^{n}_{-t} p \Rightarrow p\}$: evaluated in every state, with the set re-evaluated in every state.
* $p$ is a state predicate (a Python expression).

**Bugs to fix** (found with the real evaluator; details in §B.1):

1. The consequent's obligation is created even when the antecedent is false, so an attack **before** moving to the Cave satisfies "attack after moving".
2. Violations are silently lost when an obligation fails at a step where the antecedent is false. In the current Dragon Hunt, `attack_after_moving_to_cave` therefore **can never fail**. The existing results may be affected.
3. Off-by-one: the last state is never checked, and windows include the current state.

**Implementation:**

* A new AST node for $\square$ around a formula (possibly a $\forall$ with an implication inside).
* A plain top-level $\forall$ is evaluated only in the initial state.
* Obligations keyed by (binding, trigger step), because a new obligation can be created while a previous one for the same binding is still pending.
* Obligations of a component that no longer exists (a villager died) are dropped.
* Level-triggered constraints create an obligation in every step where the antecedent holds. If that produces many identical violation messages, deduplicate them in the feedback.

**Paper:** Sec. 4.2 states the "evaluated in the initial state" rule. Sec. 4.4.3, 4.4.4 and 4.4.7 are rewritten with an explicit $\square$, which replaces the informal "the constraint is evaluated as the system evolves". Sec. 5.2 describes the new subset.

## 6. To agree on, and next steps

**Decisions:**

1. Smart Farm: batteries and charging as in §3, with the all-drones-full initial state as the hard case.
2. Dragon Hunt: meals and regeneration as in §4, with the revised constraint set. Is `steps_since_meal` visible to the AM? (I propose yes, with hiding it as a knob.)
3. FCL: semantics and implemented subset as in §5, plus the bug fixes.
4. Paper framing: Level 0 / Level 1.
5. Acceptance target for the pilot: first-attempt pass rate ≤ ~50 % and convergence with full feedback in ≥ 80 % of the runs. Is that enough?
6. Optional: add one constraint that FCL cannot check directly but can refute (§B.7). The candidate for the running example is the Dragon Hunt "pointless trip to the Cave".

**Next steps once we agree:**

1. Fix the verifier and implement the new semantics, with small unit tests on hand-made traces (like the ones used to find the bugs).
2. Implement both extensions behind flags. New constraint files: e.g. `DSL/drones_battery_constraints.yaml`, `DSL/dragon_meals_constraints.yaml`.
3. Write a reference AM for each use case that passes all constraints, which shows they can be satisfied. Then tune the parameters (charging rate, $N$, $R$).
4. Pilot: about 5 runs × 2 models, "both" prompt, full feedback. Adjust the difficulty (§B.6).
5. Full experiments with more repetitions (success rate, median iterations, confidence intervals, as R1 asked).

---

# Part II: Details and backup options

## B.1 The current verifier and its bugs

Relevant code: [DSL/constraints/evaluation.py](../DSL/constraints/evaluation.py), [parser.py](../DSL/constraints/parser.py), [constraint.py](../DSL/constraints/constraint.py), grammar `grammar-simple.lark`.

**How it works today:**

* A future window (`TemporalWithin`) keeps **one obligation per binding for the whole run**. The obligation is created the first time the formula is evaluated (`if bound_variables not in self.obligations`).
* A past window in an antecedent (`TemporalHistory`) keeps a rolling history per binding and is re-evaluated every step. A newly spawned component starts with an empty history. The history window currently includes the current step.
* A top-level $\forall$ re-evaluates its set every step. The body is evaluated for every current member, but because obligations are keyed by binding, each component effectively gets its obligation once, from its first appearance. A component that disappears stops being evaluated, and its pending obligation is never reported.
* The grammar has no `and`/`or` between temporal operators, but conditions can be combined inside the Python expression.

**Bugs.** I confirmed these by running the real parser and evaluator on two short hand-made traces, using a temporary script outside the repository. The formula was `consequent(1, moved) implies once(attacked)`, the shape of `attack_after_moving_to_cave`.

1. **The obligation is created even if the antecedent is false.** `Implies.evaluate` evaluates the right-hand side first. *Trace:* attack at step 0, move at step 2, no attack afterwards → no violation.
2. **Violations are silently lost.** When the obligation resolves as violated at a step where the antecedent is false, `Implies` returns `True`. `check_end` then skips the obligation because it is already marked `resolved`. *Trace:* the warrior moves at step 1 and never attacks → no violation.
3. **Off-by-one.** An obligation created at step `s` with window `MAX` gets `end_step = s + MAX − 1`, so the last state is never checked. The window includes the creation step (non-strict).
4. **Minor:** an obligation is not resolved early once it has $n$ occurrences.

## B.2 Coverage of the planned constraints by the proposed subset

| Constraint | Form | Note |
| --- | --- | --- |
| Game is won | $\lozenge^{1}_{\mathit{MAX}}\, (\mathit{dragon}.\mathit{hp} \le 0)$ | |
| Attack within the first 15 steps | $\lozenge^{1}_{15}\, (\lvert \mathit{Attack} \rvert \ge 1)$ | One obligation |
| All warriors go to the Cave | $\square\, (\forall w \in \mathit{Warriors}: w.\mathit{location} = \mathit{Village} \wedge \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave}))$ | Covers spawned warriors and warriors returning from meals; the $\mathit{MAX} > 0$ guard handles the last state |
| All farmers stay in the Village | $\square\, (\forall f \in \mathit{Farmers}: f.\mathit{location} = \mathit{Village})$ | Set re-evaluated in every state |
| Spawn a few warriors | $\lozenge^{3}_{\mathit{MAX}}\, (\lvert \mathit{SpawnWarrior} \rvert \ge 2)$ | |
| Attack after each trip to the Cave | $\square\, (\forall w \in \mathit{Warriors}: w \in \mathit{GoToCave} \wedge \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{Attack}))$ | $\mathit{GoToCave}$ membership lasts one step, so it triggers once per trip |
| Eat at least every 8 steps | $\square\, (\forall v \in \mathit{Villagers}: \lozenge^{8}_{-8}\, (v \notin \mathit{Eat}) \Rightarrow v \in \mathit{Eat})$ | Per-component past window; spawned villagers start with an empty history |
| Dragon not left alone 3 steps in a row | $\square\, (\lozenge^{2}_{-2}\, \mathit{gap} \Rightarrow \neg \mathit{gap})$ | Global, level-triggered |
| Farm: overprotection, idle, consistency, closeness, coverage | top-level $\square$ / $\lozenge^{n}_{\mathit{MAX}}$ over the fixed fields | Unchanged; fields and drones are not spawned |
| No drone runs out of battery | $\forall d \in \mathit{Drones}: \square\, (d.\mathit{state} \neq \mathit{terminated})$ | Drones are not spawned, so the plain top-level $\forall$ is enough |
| Low battery → charge within 3 steps | $\square\, (\forall d \in \mathit{Drones}: d.\mathit{battery} \le 0.2 \wedge d \notin \mathit{Charging} \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging}))$ | Level-triggered: being pulled away from the charger triggers again |
| Charging not interrupted | $\square\, (\forall d \in \mathit{Drones}: d.\mathit{state} = \mathit{charging} \wedge d.\mathit{battery} < 0.9 \Rightarrow d \in \mathit{Charging})$ | |
| Most threatened field always fully protected | $\square\, (\lvert \mathit{Protecting}(\mathit{mtf}) \rvert \ge \mathit{mtf}.\mathit{drones\_for\_full\_protection})$ | Unchanged existing constraint, kept with batteries |
| *Fallback:* most threatened field not unprotected for more than 5 steps | $\square\, (\lozenge^{5}_{-5}\, \mathit{under}(\mathit{mtf}) \Rightarrow \neg \mathit{under}(\mathit{mtf}))$ | Only if the reference AM cannot satisfy the strict version |

**Things the implementation must define:**

* Obligations are keyed by (binding, trigger step), because the antecedent can hold again while a previous obligation for the same binding is still pending.
* Obligations of a component that ceased to exist are dropped.
* A trigger in the final state gives an empty future window; such constraints need the $\mathit{MAX} > 0$ guard.

**Migration of the existing constraints.** With "evaluated in the initial state", a plain top-level $\forall$ no longer covers spawned components. The constraints that should cover them must move inside $\square$; otherwise they silently stop covering spawned villagers:

* `attack_after_moving_to_cave` → $\square\, (\forall w \in \mathit{Warriors}: w \in \mathit{GoToCave} \wedge \mathit{MAX} > 0 \Rightarrow \ldots)$.
* `all_warriors_should_go_to_cave` → $\square\, (\forall w \in \mathit{Warriors}: w.\mathit{location} = \mathit{Village} \wedge \mathit{MAX} > 0 \Rightarrow \ldots)$.
* `all_farmers_should_stay_in_village` → $\square\, (\forall f \in \mathit{Farmers}: \ldots)$.
* The farm constraints are unchanged.

## B.3 Rejected alternatives for re-arming obligations

* **(a) One obligation per binding, deleted when its window ends.** It can miss violations even with $n = 1$. Example: with $d.\mathit{battery} \le 0.2 \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging})$, the battery is low at steps $i$ and $i+1$ and the drone charges only at $i+1$. The trigger at $i+1$ needs charging in $i+2 \ldots i+4$, but it is swallowed, so the drone can be pulled away at $i+2$ unnoticed. It also turns a top-level $\lozenge^{1}_{15}$ into "one attack in every 15-step block", and an obligation re-armed in the last state fails on its empty window.
* **(b) One pending obligation per binding, deleted when resolved.** This is exact for $n = 1$, but a top-level $\lozenge^{1}_{\mathit{MAX}}$ (`once`) would re-arm as soon as it is satisfied, unless top-level formulas are treated differently.
* **Keeping today's convention (a top-level $\forall$ covers spawned components implicitly).** It works, but it makes the top-level $\forall$ behave differently from other top-level formulas. With an explicit $\square$, the $\forall$ inside it covers spawned components by the normal semantics.
* **Skipping redundant obligations as an optimisation.** It is not needed, because there are at most $t$ pending obligations per binding.
* **Entering and leaving sets $S^{+}$ / $S^{-}$** (proposed by MT, rejected by the team, because explicit $\square$ is enough).
  * *Definition:* $S^{+}_{i} = S_i \setminus S_{i-1}$ and $S^{-}_{i} = S_{i-1} \setminus S_i$, with $S_{-1} = \emptyset$. $\forall x \in S^{+}: \varphi$ checks $\varphi$ at the state where $x$ enters $S$; the initial members enter at $s_0$.
  * *Motivation:* with "a constraint is evaluated in the initial state", a plain top-level $\forall$ covers only the initial components. $S^{+}$ would anchor a formula at the step where each component appears, explicitly in the syntax.
  * *Why it is not needed:* putting the $\forall$ inside $\square$ re-evaluates the set in every state, which covers spawned components. Every constraint that used $S^{+}$ / $S^{-}$ has a $\square$ form (§B.2). For example, $\forall d \in \mathit{LowBattery}^{+}: \lozenge^{1}_{3}\, (d \in \mathit{Charging})$ becomes $\square\, (\forall d \in \mathit{Drones}: d.\mathit{battery} \le 0.2 \wedge d \notin \mathit{Charging} \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging}))$.
  * *What is lost:* "exactly once, from when the component appears" now needs a state condition that marks the moment (e.g. "in the Village"), or an attribute such as `age == 0`. Conditions that hold over several steps create an obligation in each of those steps, which means more obligations and possibly duplicate violation messages.
  * *Pitfalls found while analysing it* (for the record): with $\mathit{Eat}^{+}$, a villager eating in two consecutive steps would satisfy its obligation and never re-trigger, so $\mathit{Eat}^{-}$ would be needed. Edge triggers can also be fooled by oscillation, e.g. a most threatened field that alternates every step would satisfy each obligation by leaving the set. Level-triggered $\square$ forms do not have these problems.

## B.4 Dragon Hunt: Level 1 constraint set

| Constraint | Level 1 | Note |
| --- | --- | --- |
| Game is won | keep | |
| Dragon attacked within the first 15 steps | keep | Now interacts with the first meal and the second warrior |
| All warriors go to the Cave | keep | Moved inside $\square$, so it covers spawned warriors |
| All farmers stay in the Village | keep | Eating is in the Village, so there is no conflict |
| Spawn a few warriors / farmers | keep warriors, maybe drop farmers | Spawning warriors is needed anyway for staggered meals |
| Attack after moving to the Cave | keep | Moved inside $\square$, triggers on every trip |
| Warriors are mostly in the Cave (80 %) | **drop** | Conflicts with meals; replaced by the no-gap constraint |
| Every villager eats every 8 steps | **new** | Per-component past window |
| Dragon not left alone 3 steps in a row | **new** | Global past window |
| No attacks with fewer than 3 villagers (shield) | knob | Only if too easy |

**Satisfiability (rough check, to be confirmed with the reference AM):** with one warrior, every meal creates a 3-step gap, so the AM needs a second warrior before the first meal is due. Two farmers produce 10 wheat in the first step, which together with the initial 10 wheat pays for a warrior (12) in step 2. So this is achievable well before step 8.

**Observability of `steps_since_meal`:** exposing it is the most transparent option, and the difficulty then comes from planning and coordination only. Hiding it is still fair, because the rule is stated and the AM can keep its own state, but it adds a memory requirement. I suggest exposing it first and keeping "hidden" as a knob.

## B.5 Backup options

### Smart Farm

* **F2: minimum dwell time / anti-oscillation** (constraints only). For example: "a drone stays on a field for at least 10 steps unless its battery is low", or "a drone is reassigned at most twice in 20 steps" (past window). On its own this is probably too easy, because GPT-6 Luna already keeps drones on their fields; it is stronger together with batteries. It can look arbitrary unless it is motivated by flight costs. *Knob if the battery extension is too easy.*
* **F3: field values or heterogeneous drones.** Field values are cheap but LLMs handle a weighted sort easily. Drone types need more work, because `protectionPlaces` depends on `Drone.Radius`. *Skip.*
* **F4: faster changes in bird behaviour** (`birdFieldProbabilities` every 30 instead of 100 steps; configuration only). It increases the pressure on handover and consistency. *Possible extra initial state.*
* **Initial states with low or random batteries:** comparatively easy, because reactive charging handles them. All-full is the hard case (§3).
* **Limited charger capacity:** not planned (the simple version has unlimited capacity). It would add queueing on top of pre-charging. *Knob if too easy.*
* **"No needless charging" constraint** (no charging above 50 % battery): **dropped**, because it conflicts with the pre-charging we want.

### Dragon Hunt

* **D1: automatic food upkeep** (every villager eats 1 wheat per step). It is just lower wheat production: the AM only needs a reserve before spawning, and starvation rarely happens. *Too easy on its own;* its useful part lives on in the meals.
* **D1.1: food transport to the Cave.** Villagers carry wheat to a pantry in the Cave, and warriors eat there. It is a supply chain with periodic runs, which requires dropping "farmers stay in the Village". It is the same kind of difficulty as meals, but needs more changes (a pantry component and new ensembles). *Main alternative if meals do not work.*
* **D2: the Dragon's shield** (damage only with ≥ 3 simultaneous attackers). It is tiny to implement. On its own it is a static rule; with meals and regeneration it becomes a scheduling problem, since at least 3 must keep attacking while others eat. Constraint: $\square\, (\lvert \mathit{Attack} \rvert = 0 \vee \lvert \mathit{Attack} \rvert \ge 3)$. *Knob.*
* **D3: healing and retreat** (a `Heal` group in the Village; injured warriors retreat). The trigger is the current HP, so it is a reactive rule, and HP loss is random. *Easier than meals.*
* **D4: multi-step travel** (2–3 steps between the Village and the Cave). It needs a third "travelling" set and changes the assignment structure; the meals already create a 3-step absence. *Not recommended.*
* **D5: Dragon phases** (sleeping / enraged). It is a reactive rule that strong models handle easily. *Not recommended.*
* **Weapon durability** (repair after $k$ attacks): same structure as meals, but it counts events and is harder to express in FCL. **Cave capacity**: a strong knob, but it risks becoming a puzzle. **Spawn cooldown**: adds little. *Not recommended.*

### Both use cases

* **C1: more initial states.** Useful in combination, e.g. villagers starting with uneven hunger, low initial wheat, fast-changing birds. Only add states that can be satisfied; avoid degenerate ones (fewer drones than the most threatened field needs, fewer than two initial villagers), and do not add too many, because each one increases simulation time.
* **C2: less detailed strategy text.** *Rejected:* the strategy and the requirements must carry the same information.
* **C3: tighter thresholds on existing constraints** (e.g. coverage ≥ 0.9). They look arbitrary, can become unsatisfiable, and turn the task into optimisation. *Not recommended.*
* **C4: larger scale** (more fields and drones). Little effect on the logic; mostly longer simulations. *Not recommended.*
* **C5: unstated parameters** (e.g. the charging rate not given). Likely to be seen as making the task deliberately hard. *Not recommended.*

## B.6 Pilot and calibration

1. Implement behind flags (e.g. `meal_interval: null`, `dragon.Regeneration: 0`, batteries on or off), so that Level 0 stays reproducible.
2. Write a reference AM per use case that passes all constraints on all initial states. It shows the constraints can be satisfied and supports the alignment argument in Sec. 5.5.2. For the farm, adapt [`most_threatened.py`](/generated_adaptations/farm/mock/most_threatened.py) or [`protect_by_threat.py`](/generated_adaptations/farm/mock/protect_by_threat.py).
3. Pilot: about 5 runs × 2 models (GPT-6 Luna and one cheaper model), "both" prompt, full feedback. Accept the variant if:
   * the first-attempt pass rate is ≤ ~50 %;
   * full feedback converges within ≤ 5–6 iterations in ≥ 80 % of the runs;
   * metrics-only feedback is noticeably worse.
4. Adjust the difficulty:
   * **Too easy:** Farm → F2 dwell time, limited charger capacity. Dragon → hide `steps_since_meal`, then the shield (D2), or switch to food transport (D1.1).
   * **Too hard:** Farm → faster charging, then relax "most threatened field always fully protected" to "never unprotected for more than 5 steps in a row". Dragon → larger $N$, a longer allowed gap than 3, smaller $R$, start with 2 warriors.
5. Full experiments with enough repetitions for R1.

## B.7 Constraints that FCL cannot check directly, but can refute (idea)

*Status: idea for discussion, suggested by a colleague. Not part of the main proposal yet.*

**The idea.** So far, every constraint's reason (its meaning) and its FCL formula say the same thing. Here we look for constraints where they differ:

* The **constraint** $P$ is something we want but cannot express in FCL directly.
* The **check** is an FCL formula $\varphi$ with $P \Rightarrow \varphi$. So a violation of $\varphi$ implies a violation of $P$, and the reason message talks about $P$.
* Passing $\varphi$ does not prove $P$. The check is **sound but incomplete**: it reports only real violations, but it may miss some.

**When is $P$ out of FCL's reach?** FCL looks at one observed run and its states. $P$ is outside that when it talks about:

* **possible futures**: "whatever the AM does from now on, X will happen". These are points of no return, i.e. the AM has already made a violation inevitable.
* **alternative decisions**: "no other decision would have been better", i.e. optimality.

In both cases, domain knowledge (travel times, energy model, damage) lets us write a predicate that is a necessary condition for $P$. FCL's syntax does not change; only the relation between the reason and the formula does.

**Why it is useful for vibe coding.** A point-of-no-return check fires **at the decision that caused the problem**, not when the consequence finally appears several steps later. The feedback can then name the wrong decision. This also fits the paper's Sec. 5.5.5, where the AM could use the pending obligations to avoid such states.

### Dragon Hunt candidates (with meals)

**(1) Pointless trip to the Cave (recommended for the running example).**

* **Constraint $P$:** "A warrior is sent to the Cave only if the trip can still be useful, i.e. it can attack before it has to return to eat."
* **Why FCL cannot check it directly:** it speaks about all possible continuations. Whatever the AM does later, this warrior will either starve or never attack on this trip.
* **Check:** the meal rule allows at most $N$ steps without a meal (§4), and the timing is deterministic:
  * the warrior sent at step $t$ arrives in the Cave at $t+1$;
  * it must leave one step before its meal;
  * so it can attack at least once only if it was sent with $\mathit{stepsSinceMeal} \le N - 2$.

  The check is:

  $\square\, (\forall w \in \mathit{Warriors}: w \in \mathit{GoToCave} \Rightarrow w.\mathit{stepsSinceMeal} \le N - 2)$

  The exact bound depends on how the counter is defined; fix it once meals are implemented.
* **Example reason:** "Warrior John was sent to the Cave at step 12, but he must eat by step 15 and cannot attack before he has to come back. Let him eat first."
* **Soundness:** if the check fails, then whatever happens next, the trip violates either "attack after each trip to the Cave" or "eat every $N$ steps", unless the game ends or the warrior dies first. That is why $P$ is phrased as "can still be useful".
* **Why it is a good example:**
  * it is simple and specific to the Dragon Hunt;
  * it fires at the decision step, which is earlier than either of the two constraints it protects;
  * it shows a typical first-attempt mistake (greedy "send every warrior to the Cave");
  * it captures a *conflict between two obligations*, which no single existing constraint describes.

**(2) The game can no longer be won.**

* **Constraint $P$:** "The AM never brings the game into a state from which it cannot be won."
* **Why FCL cannot check it directly:** this needs *some* future strategy that still wins, which is a quantification over possible futures. The random counterattacks make it harder still.
* **Check:** an optimistic upper bound on the damage that can still be dealt, $\square\, (\mathit{dragon}.\mathit{hp} \le \mathit{maxDamage}(\mathit{state}, \mathit{MAX}))$.
  * `maxDamage` is a small Python helper that runs a *relaxed* game for $\mathit{MAX}$ steps.
  * In the relaxed game, every villager attacks as a warrior in every step, spawning is limited only by wheat and by the rule of 2 villagers per newborn, farming is at the maximum rate, and there is no travel, no meals, no counterattacks and no regeneration.
  * All of these relaxations only overestimate the damage, so a violation is real.
* **Example reason:** "At step 18 the game could no longer be won: the Dragon has 41 HP, but even in the best case at most 36 damage can be dealt in the remaining 12 steps."
* **Assessment:** it is a natural constraint and gives earlier, more diagnostic feedback than "the game is won" at step 30. But the bound is loose, so it fires late, and the relaxed game is harder to explain in the paper than (1).

**(3) Dragon left alone inevitably** (possible extension of the no-gap constraint).

* **Idea:** a violation of "never 3 steps without an attack" is already inevitable when, in the next 2 steps, every warrior in the Cave must leave to eat and no warrior can arrive in time.
* **Check:** count the warriors who will be able to attack in each of the next steps, given their meal deadlines and travel time.
* **Assessment:** sound and very diagnostic, but the counting predicate is more complex than (1).

**Considered and dropped:** "a warrior in the Cave can no longer get home in time to eat". With 1-step travel it fires in the same step as the meal constraint itself, so it gives no earlier feedback. It would become useful with longer travel (D4).

### Smart Farm candidates (with batteries)

**(4) A drone can no longer reach the charger.**

* **Constraint $P$:** "The AM never strands a drone, i.e. no drone ever gets into a state where running out of battery is inevitable."
* **Check:** $\square\, (\forall d \in \mathit{Drones}: d.\mathit{state} \notin \{\mathit{charging}, \mathit{terminated}\} \Rightarrow d.\mathit{battery} \ge d.\mathit{energyToCharger})$, with `energyToFlyToCharger()` already in [drone.py](../farm/components/drone.py).
* **Benefit:** it fires as soon as the drone is lost, which is up to a whole flight earlier than "no drone runs out of battery".
* **Example reason:** "Drone_4 can no longer reach the charger: it needs 0.08 battery to fly there but has only 0.06."

**(5) Distance-optimal assignment** (alternative decisions).

* **Constraint $P$:** "Drones are assigned to fields so that the total flight distance is minimal."
* **Why FCL cannot check it directly:** this quantifies over all alternative assignments (NP-hard in general).
* **Check:** no improving pairwise swap: $\square\, (\forall d_1, d_2: \mathit{dist}(d_1, f(d_1)) + \mathit{dist}(d_2, f(d_2)) \le \mathit{dist}(d_1, f(d_2)) + \mathit{dist}(d_2, f(d_1)))$.
* **Example reason:** "The assignment is not distance-optimal: Drone_3 and Drone_5 could swap fields and fly 12.4 less in total."
* **Notes:** it would replace or generalise today's `closeness` constraint. It needs a nested $\forall$, so that the reason can name both drones.

**(6) Energy budget.**

* **Constraint $P$:** "The most threatened field can be kept fully protected until the end."
* **Check:** a drone-step energy budget. Protecting drones cannot charge, so: $\square\, (\sum_d d.\mathit{battery} + \mathit{rate} \cdot (\lvert \mathit{Drones} \rvert - \mathit{need}) \cdot \mathit{MAX} \ge \mathit{hover} \cdot \mathit{need} \cdot \mathit{MAX})$
* **Assessment:** sound, but probably too loose to fire often.

### Caveats

* **Soundness depends on the domain model** used in the predicate (travel times, energy consumption, damage). If the model in the check is wrong, the check can report false violations. The predicates should therefore use the simulator's own functions (e.g. `energyToFlyToCharger`), not re-implement them.
* **The verifier needs the relevant state even if the AM does not see it**, e.g. `steps_since_meal` when it is hidden as a difficulty knob.
* **Guards for the end of the run.** A trip that starts in the last steps cannot fail "attack after the trip" anyway, so (1) may need a $\mathit{MAX}$ guard to stay consistent with the other constraints.
* **Paper:** one example (preferably (1)) in Sec. 4.4, and a short paragraph on sound-but-incomplete checks of properties that cannot be monitored on a single run. That links to the monitorability discussion in runtime verification ([8]).
