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
| **FCL / verifier** | Explicit "globally", new entering/leaving sets $S^{+}$ / $S^{-}$, strict windows, bug fixes | Gives consistent semantics for repeating constraints and for spawned components. Also needed to state the new constraints. |
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

**Example constraints** (FCL notation; $\forall x \in S^{+}$, $\square$ and strict windows as defined in §5):

* *No drone runs out of battery:* $\forall d \in \mathit{Drones}: \square\, (d.\mathit{state} \neq \mathit{terminated})$
* *A drone that runs low goes to charge within 3 steps:* $\forall d \in \mathit{LowBattery}^{+}: \lozenge^{1}_{3}\, (d \in \mathit{Charging})$, where $\mathit{LowBattery} = \{d \in \mathit{Drones} \mid d.\mathit{battery} \le 0.2 \wedge d \notin \mathit{Charging}\}$. Pulling a drone away from the charger makes it re-enter $\mathit{LowBattery}$, which triggers the constraint again.
* *Charging is not interrupted:* $\forall d \in \mathit{Charging}^{-}: d.\mathit{battery} \ge 0.9$ (a drone leaves the charger only when charged).
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
* *All warriors go to the Cave, including spawned ones:* $\forall w \in \mathit{Warriors}^{+}: \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave})$.
* *Every time a warrior goes to the Cave, it attacks afterwards:* $\forall w \in \mathit{GoToCave}^{+}: \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{Attack})$.

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
3. **Entering and leaving sets.** $S^{+}_{i} = S_i \setminus S_{i-1}$ and $S^{-}_{i} = S_{i-1} \setminus S_i$, with $S_{-1} = \emptyset$. $\forall x \in S^{+}: \varphi$ checks $\varphi$ at the state where $x$ enters $S$. $S^{+}$ includes the initial members, because they enter at $s_0$. This covers spawned components and gives "every time X happens" constraints. A plain $\forall x \in S$ at the top level covers only the initial components.
4. **All windows are strict** (the current state is excluded) in both directions.

**Examples showing the difference:**

* $\lozenge^{1}_{15}\, (\lvert \mathit{Attack} \rvert \ge 1)$: one obligation for the first 15 steps; it is not repeated.
* $\forall w \in \mathit{Warriors}^{+}: \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave})$: one obligation per warrior, from the step it appears.
* $\square\, (d.\mathit{battery} \le 0.2 \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging}))$: a new obligation in every step where the battery is low.
* $\forall d \in \mathit{LowBattery}^{+}: \lozenge^{1}_{3}\, (d \in \mathit{Charging})$: a new obligation every time the drone enters $\mathit{LowBattery}$.

**Implemented subset** (enough for all planned constraints; the coverage check is in §B.2):

* $[\forall x \in S \mid S^{+} \mid S^{-}:]\ B$ with $B \in \{p,\ \lozenge^{n}_{t} p,\ p \Rightarrow \lozenge^{n}_{t} p\}$: evaluated once at the anchor state, i.e. $s_0$ or the element's entry or exit.
* $\square\, ([\forall x \in S:]\ R)$ with $R \in \{p \Rightarrow \lozenge^{n}_{t} p,\ \lozenge^{n}_{-t} p \Rightarrow p\}$: evaluated in every state.
* $p$ is a state predicate (a Python expression). Set operations ($\setminus$, $\cup$) are not needed.

**Bugs to fix** (found with the real evaluator; details in §B.1):

1. The consequent's obligation is created even when the antecedent is false, so an attack **before** moving to the Cave satisfies "attack after moving".
2. Violations are silently lost when an obligation fails at a step where the antecedent is false. In the current Dragon Hunt, `attack_after_moving_to_cave` therefore **can never fail**. The existing results may be affected.
3. Off-by-one: the last state is never checked, and windows include the current state.

**Implementation:**

* New AST nodes for $\square$ around a formula and for $\forall x \in S^{+}$ / $S^{-}$ (keeping the previous step's set and comparing components by identity).
* Obligations keyed by (binding, anchor step).
* Obligations of a component that no longer exists (a villager died) are dropped.
* Duplicate violation messages are removed from the feedback if they become noisy.

**Paper:** Sec. 4.2 gets $S^{+}$ / $S^{-}$ and states the "evaluated in the initial state" rule. Sec. 4.4.3, 4.4.4 and 4.4.7 are rewritten with $\square$ and $^{+}$, which replaces the informal "the constraint is evaluated as the system evolves". Sec. 5.2 describes the new subset.

## 6. To agree on, and next steps

**Decisions:**

1. Smart Farm: batteries and charging as in §3, with the all-drones-full initial state as the hard case.
2. Dragon Hunt: meals and regeneration as in §4, with the revised constraint set. Is `steps_since_meal` visible to the AM? (I propose yes, with hiding it as a knob.)
3. FCL: semantics and implemented subset as in §5, plus the bug fixes.
4. Paper framing: Level 0 / Level 1.
5. Acceptance target for the pilot: first-attempt pass rate ≤ ~50 % and convergence with full feedback in ≥ 80 % of the runs. Is that enough?

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
| All warriors go to the Cave | $\forall w \in \mathit{Warriors}^{+}: \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{GoToCave})$ | Guard for warriors spawned in the last state |
| All farmers stay in the Village | $\square\, (\forall f \in \mathit{Farmers}: f.\mathit{location} = \mathit{Village})$ | Set re-evaluated in every state |
| Spawn a few warriors | $\lozenge^{3}_{\mathit{MAX}}\, (\lvert \mathit{SpawnWarrior} \rvert \ge 2)$ | |
| Attack after each trip to the Cave | $\forall w \in \mathit{GoToCave}^{+}: \mathit{MAX} > 0 \Rightarrow \lozenge^{1}_{\mathit{MAX}}\, (w \in \mathit{Attack})$ | Edge-triggered, re-arms on every trip |
| Eat at least every 8 steps | $\square\, (\forall v \in \mathit{Villagers}: \lozenge^{8}_{-8}\, (v \notin \mathit{Eat}) \Rightarrow v \in \mathit{Eat})$ | Alternative with entering/leaving sets: $\forall v \in \mathit{Villagers}^{+}: \lozenge^{1}_{8}\, (v \in \mathit{Eat})$ plus $\forall v \in \mathit{Eat}^{-}: \lozenge^{1}_{8}\, (v \in \mathit{Eat})$. Use $\mathit{Eat}^{-}$, not $\mathit{Eat}^{+}$: with $\mathit{Eat}^{+}$, eating in two consecutive steps would satisfy the obligation and it would never re-trigger |
| Dragon not left alone 3 steps in a row | $\square\, (\lozenge^{2}_{-2}\, \mathit{gap} \Rightarrow \neg \mathit{gap})$ | Global, level-triggered |
| Farm: overprotection, idle, consistency, closeness, coverage | top-level $\square$ / $\lozenge^{n}_{\mathit{MAX}}$ over the fixed fields | Unchanged; fields and drones are not spawned |
| No drone runs out of battery | $\forall d \in \mathit{Drones}: \square\, (d.\mathit{state} \neq \mathit{terminated})$ | Alternatively: $\mathit{Drones}^{-}$ is always empty, if terminated drones are removed |
| Low battery → charge within 3 steps | $\forall d \in \mathit{LowBattery}^{+}: \lozenge^{1}_{3}\, (d \in \mathit{Charging})$ | $d \notin \mathit{Charging}$ must be part of $\mathit{LowBattery}$, so that being pulled away from the charger re-triggers |
| Charging not interrupted | $\forall d \in \mathit{Charging}^{-}: d.\mathit{battery} \ge 0.9$ | |
| Most threatened field always fully protected | $\square\, (\lvert \mathit{Protecting}(\mathit{mtf}) \rvert \ge \mathit{mtf}.\mathit{drones\_for\_full\_protection})$ | Unchanged existing constraint, kept with batteries |
| *Fallback:* most threatened field not unprotected for more than 5 steps | $\square\, (\lozenge^{5}_{-5}\, \mathit{under}(\mathit{mtf}) \Rightarrow \neg \mathit{under}(\mathit{mtf}))$ | Only if the reference AM cannot satisfy the strict version. Must stay level-triggered, see below |

**Limitation of edge triggers.** Requirements like "never $k$ steps in a row in a bad situation" must stay level-triggered ($\square$ with a past window). For example, the edge-triggered $\forall f \in \mathit{UnderprotectedMTF}^{+}: \lozenge^{1}_{5}\, (f \notin \mathit{UnderprotectedMTF})$ is fooled when the most threatened field alternates between two fields every step: each obligation is satisfied by the field leaving the set, and no field is ever protected.

**Things the implementation must define:**

* Obligations are keyed by (binding, anchor step), because an element can re-enter a set while its previous obligation is still pending.
* $S^{+}$ / $S^{-}$ are computed by comparing with the previous step's set, by component identity.
* Obligations of a component that ceased to exist are dropped.
* An element that enters a set in the final state gets an empty future window; such constraints need the $\mathit{MAX} > 0$ guard.

**Migration of the existing constraints:**

* `attack_after_moving_to_cave` becomes the $\mathit{GoToCave}^{+}$ form.
* `all_warriors_should_go_to_cave` becomes $\mathit{Warriors}^{+}$.
* `all_farmers_should_stay_in_village` becomes $\square\, (\forall f \in \mathit{Farmers}: \ldots)$.
* The farm constraints are unchanged.

## B.3 Rejected alternatives for re-arming obligations

* **(a) One obligation per binding, deleted when its window ends.** It can miss violations even with $n = 1$. Example: with $d.\mathit{battery} \le 0.2 \Rightarrow \lozenge^{1}_{3}\, (d \in \mathit{Charging})$, the battery is low at steps $i$ and $i+1$ and the drone charges only at $i+1$. The trigger at $i+1$ needs charging in $i+2 \ldots i+4$, but it is swallowed, so the drone can be pulled away at $i+2$ unnoticed. It also turns a top-level $\lozenge^{1}_{15}$ into "one attack in every 15-step block", and an obligation re-armed in the last state fails on its empty window.
* **(b) One pending obligation per binding, deleted when resolved.** This is exact for $n = 1$, but a top-level $\lozenge^{1}_{\mathit{MAX}}$ (`once`) would re-arm as soon as it is satisfied, unless top-level formulas are treated differently.
* **Keeping today's convention (a top-level $\forall$ covers spawned components implicitly).** It works, but it makes the top-level $\forall$ behave differently from other top-level formulas. $S^{+}$ makes this explicit.
* **Skipping redundant obligations as an optimisation.** It is not needed, because there are at most $t$ pending obligations per binding.

## B.4 Dragon Hunt: Level 1 constraint set

| Constraint | Level 1 | Note |
| --- | --- | --- |
| Game is won | keep | |
| Dragon attacked within the first 15 steps | keep | Now interacts with the first meal and the second warrior |
| All warriors go to the Cave | keep | Rewritten with $\mathit{Warriors}^{+}$ |
| All farmers stay in the Village | keep | Eating is in the Village, so there is no conflict |
| Spawn a few warriors / farmers | keep warriors, maybe drop farmers | Spawning warriors is needed anyway for staggered meals |
| Attack after moving to the Cave | keep | Rewritten with $\mathit{GoToCave}^{+}$, re-arms on every trip |
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
