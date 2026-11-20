# Dragon Hunt

Simulation of a Dragon Hunt game in which the player controls villagers with the goal of killing a dragon.

A detailed description of the scenario can be found [here](./configs/description2.yaml); the same information is presented to the LLM.

## Rules and parameters

The parameters are set in [`configs/default.yaml`](./configs/default.yaml).

* **Villagers.** Farmers produce more wheat, warriors deal more damage. New villagers are spawned from wheat: 12 for a warrior, 10 for a farmer. Moving between the Village and the Cave takes one step.
* **Meals** (`meals`). Every villager must eat in the Village (group `"eat"`, 1 wheat) at least once in every `interval` consecutive steps.
  * A villager that has not eaten for longer **starves**: they lose `starvation_damage` HP in each step.
  * With `hungry_cannot_attack`, starving villagers also deal no damage to the Dragon.
  * `interval: null` disables the meals.
* **The Dragon** (`dragon`). It counterattacks the villagers in the Cave. After it is attacked for the first time, it **regenerates** `Regeneration` HP in each step in which nobody attacks it.
* **The game** is won when the Dragon is killed within `steps` (30) steps.

Current parameters: Dragon HP = 100, meal interval N = 6, regeneration R = 5, `hungry_cannot_attack: true`, 30 steps.

## Baselines

Hand-written adaptation managers in [`generated_adaptations/dragon/mock`](../generated_adaptations/dragon/mock):

| Baseline | Strategy |
| --- | --- |
| [`greedy_no_meals`](../generated_adaptations/dragon/mock/greedy_no_meals.py) | All warriors attack, the farmers farm and spawn new villagers, nobody ever eats. |
| [`greedy_with_meals`](../generated_adaptations/dragon/mock/greedy_with_meals.py) | Like `greedy_no_meals`, but the villagers eat when they would otherwise starve: warriors return from the Cave just in time to eat. There is no coordination of the meals and no wheat reserve. |
| [`greedy_with_reserve`](../generated_adaptations/dragon/mock/greedy_with_reserve.py) | Like `greedy_with_meals`, but it keeps a constant reserve of 3 wheat for the meals and spawns only from the wheat above it. |
| [`greedy_eat_last`](../generated_adaptations/dragon/mock/greedy_eat_last.py) | Like `greedy_with_meals`, but it decides about spawning before the meals and sends the villagers to eat without checking that there is wheat left (a likely mistake of a generated AM). Eating then fails when the wheat was spent on spawning. |
| [`staggered_meals`](../generated_adaptations/dragon/mock/staggered_meals.py) | The reference strategy. It keeps attacking continuously and staggers the warriors' meals, so that the Dragon is not left unattacked (a warrior is sent back to eat at most one attack earlier, so every trip has at least two attacks). It reserves wheat for the meals that are due, and a warrior that is too hungry eats before going to the Cave. |
| [`assemble_and_strike`](../generated_adaptations/dragon/mock/assemble_and_strike.py) | The warriors gather in the Village, eat, and attack together in waves (4 warriors, or all of them from step 10). The whole wave returns to eat together, which leaves gaps between the waves. |

## Tuning of the parameters

The parameters were tuned with [`tuning.py`](./tuning.py) (`python dragon/tuning.py`, run from the repository root). For each parameter combination and baseline, it reports:

* the win rate, the average number of steps to win, and the average remaining HP of the Dragon in lost games, over 10 runs (seeds 1–10) from the default initial state;
* the functional constraints violated in the 6 test situations from [`DSL/dragon.yaml`](../DSL/dragon.yaml), with the number of situations in which each was violated.
  * The required constraints are in [`DSL/dragon_constraints.yaml`](../DSL/dragon_constraints.yaml). The optional ones, marked "(opt.)", are in [`DSL/dragon_constraints_optional.yaml`](../DSL/dragon_constraints_optional.yaml): `attack_at_least_once_during_first_half`, `no_pointless_trip_to_cave`, `leave_cave_in_time` and `keep_attacking`.
  * The situations are seeds 1–3, `no_initial_warriors`, `initial_wheat=15` and `initial_wheat=15,seed=1` (the default setup, only with a different initial amount of wheat).

### Selected parameters

These are the chosen parameters (see below for the grid search results and observations):

| Parameter | Value |
| --- | --- |
| Number of steps | 30 |
| Initial state | 10 wheat, 2 farmers, 1 warrior |
| Farmer | 4 HP, attack 1, farming 5, spawn cost 10 |
| Warrior | 6 HP, attack 3, farming 2, spawn cost 12 |
| Dragon | 100 HP, fire attack probability 0.4, eat attack probability 0.2, regeneration R = 5 |
| Meals | interval N = 6, cost 1 wheat, starvation damage 1, weakness (`hungry_cannot_attack`) on |

#### Baseline performance

Win rate and steps over 10 runs (seeds 1–10) from the default initial state, and the constraints violated in the 6 test situations (in how many of them). An AM is **valid** if it violates neither the system nor the required functional constraints.

The win rate and the constraints come from different games. A game lost in a run outside the test situations (seeds 4–10) does not show up as a `game_is_won` violation.

| Baseline | Win rate | Avg. steps to win | Valid | Violated system and required constraints | Violated optional constraints |
| --- | --- | --- | --- | --- | --- |
| `greedy_no_meals` | 0% (Dragon left with 100 HP) | n/a | no | `eat_regularly` (6), `game_is_won` (6), `spawn_warrior_when_none_left` (6), `keep_wheat_reserve` (2) | `leave_cave_in_time` (6) |
| `greedy_with_meals` | 100% | 19.8 | no | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2) | `no_pointless_trip_to_cave` (2) |
| `greedy_with_reserve` | 100% | 22.5 | yes | none | none |
| `greedy_eat_last` | 100% | 19.8 | no | `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2), `eat_regularly` (2), `keep_wheat_reserve` (2) | none |
| `staggered_meals` | 100% | 20.7 | yes | none | none |
| `assemble_and_strike` | 100% | 20.5 | yes | none | `keep_attacking` (6) |

`greedy_with_meals` and `greedy_eat_last` fail only in the two `initial_wheat=15` situations, where they run out of wheat for a meal (see the observations below). `greedy_with_reserve` avoids this with a constant wheat reserve, but it spawns more slowly, so it wins later.

### Grid search (Dragon HP = 100, 30 steps)

The grid covers the meal interval N, the weakness flag (`hungry_cannot_attack`) and the regeneration R. The baselines are in the columns.

#### Win rate

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_with_reserve` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | 30% | 100% | 100% | 100% | 100% | 100% |
| 6 | off | 5 | 30% | 100% | 100% | 100% | 100% | 100% |
| 6 | off | 10 | 30% | 100% | 100% | 100% | 100% | 100% |
| 6 | on | 0 | 0% | 100% | 100% | 100% | 100% | 100% |
| 6 | on | 5 | 0% | 100% | 100% | 100% | 100% | 100% |
| 6 | on | 10 | 0% | 100% | 100% | 100% | 100% | 100% |
| 8 | off | 0 | 80% | 100% | 100% | 100% | 100% | 100% |
| 8 | off | 5 | 80% | 100% | 90% | 100% | 100% | 100% |
| 8 | off | 10 | 80% | 100% | 90% | 100% | 100% | 100% |
| 8 | on | 0 | 30% | 100% | 100% | 100% | 100% | 100% |
| 8 | on | 5 | 30% | 100% | 90% | 100% | 100% | 100% |
| 8 | on | 10 | 30% | 100% | 90% | 100% | 100% | 100% |

#### Average number of steps to win

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_with_reserve` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | 14.3 | 19.5 | 22.0 | 19.5 | 20.3 | 18.8 |
| 6 | off | 5 | 14.3 | 19.8 | 22.5 | 19.8 | 20.7 | 20.5 |
| 6 | off | 10 | 14.3 | 19.9 | 23.1 | 19.9 | 20.8 | 23.0 |
| 6 | on | 0 | n/a | 19.5 | 22.0 | 19.5 | 20.3 | 18.8 |
| 6 | on | 5 | n/a | 19.8 | 22.5 | 19.8 | 20.7 | 20.5 |
| 6 | on | 10 | n/a | 19.9 | 23.1 | 19.9 | 20.8 | 23.0 |
| 8 | off | 0 | 15.2 | 17.2 | 20.2 | 17.2 | 17.9 | 18.4 |
| 8 | off | 5 | 15.5 | 17.4 | 20.0 | 17.4 | 18.1 | 19.1 |
| 8 | off | 10 | 15.5 | 17.4 | 20.1 | 17.4 | 18.1 | 19.4 |
| 8 | on | 0 | 15.3 | 17.2 | 20.2 | 17.2 | 17.9 | 18.4 |
| 8 | on | 5 | 15.7 | 17.4 | 20.0 | 17.4 | 18.1 | 19.1 |
| 8 | on | 10 | 15.7 | 17.4 | 20.1 | 17.4 | 18.1 | 19.4 |

#### Average remaining HP of the Dragon in lost games

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_with_reserve` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | 23.3 | n/a | n/a | n/a | n/a | n/a |
| 6 | off | 5 | 92.0 | n/a | n/a | n/a | n/a | n/a |
| 6 | off | 10 | 100.0 | n/a | n/a | n/a | n/a | n/a |
| 6 | on | 0 | 42.1 | n/a | n/a | n/a | n/a | n/a |
| 6 | on | 5 | 100.0 | n/a | n/a | n/a | n/a | n/a |
| 6 | on | 10 | 100.0 | n/a | n/a | n/a | n/a | n/a |
| 8 | off | 0 | 25.0 | n/a | n/a | n/a | n/a | n/a |
| 8 | off | 5 | 97.5 | n/a | 5.0 | n/a | n/a | n/a |
| 8 | off | 10 | 100.0 | n/a | 30.0 | n/a | n/a | n/a |
| 8 | on | 0 | 17.3 | n/a | n/a | n/a | n/a | n/a |
| 8 | on | 5 | 79.3 | n/a | 5.0 | n/a | n/a | n/a |
| 8 | on | 10 | 100.0 | n/a | 30.0 | n/a | n/a | n/a |

#### Violated constraints (number of test situations in which the constraint was violated; generic constraints are prefixed with "system", optional ones are marked "(opt.)")

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_with_reserve` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (5), `spawn_warrior_when_none_left` (5), `keep_wheat_reserve` (2) | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2), `no_pointless_trip_to_cave (opt.)` (2) | none | `eat_regularly` (2), `keep_wheat_reserve` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking (opt.)` (6) |
| 6 | off | 5 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (5), `spawn_warrior_when_none_left` (5), `keep_wheat_reserve` (2) | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2), `no_pointless_trip_to_cave (opt.)` (2) | none | `eat_regularly` (2), `keep_wheat_reserve` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking (opt.)` (6) |
| 6 | off | 10 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (5), `spawn_warrior_when_none_left` (5), `keep_wheat_reserve` (2) | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2), `no_pointless_trip_to_cave (opt.)` (2) | none | `eat_regularly` (2), `keep_wheat_reserve` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking (opt.)` (6) |
| 6 | on | 0 | `eat_regularly` (6), `game_is_won` (6), `leave_cave_in_time (opt.)` (6), `spawn_warrior_when_none_left` (6), `keep_wheat_reserve` (2) | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2), `no_pointless_trip_to_cave (opt.)` (2) | none | `eat_regularly` (2), `keep_wheat_reserve` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking (opt.)` (6) |
| 6 | on | 5 | `eat_regularly` (6), `game_is_won` (6), `leave_cave_in_time (opt.)` (6), `spawn_warrior_when_none_left` (6), `keep_wheat_reserve` (2) | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2), `no_pointless_trip_to_cave (opt.)` (2) | none | `eat_regularly` (2), `keep_wheat_reserve` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking (opt.)` (6) |
| 6 | on | 10 | `eat_regularly` (6), `game_is_won` (6), `leave_cave_in_time (opt.)` (6), `spawn_warrior_when_none_left` (6), `keep_wheat_reserve` (2) | `attack_after_moving_to_cave` (2), `eat_regularly` (2), `keep_wheat_reserve` (2), `no_pointless_trip_to_cave (opt.)` (2) | none | `eat_regularly` (2), `keep_wheat_reserve` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking (opt.)` (6) |
| 8 | off | 0 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (1), `spawn_warrior_when_none_left` (1) | none | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking (opt.)` (6) |
| 8 | off | 5 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (1), `spawn_warrior_when_none_left` (1) | none | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking (opt.)` (6) |
| 8 | off | 10 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (1), `spawn_warrior_when_none_left` (1) | none | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking (opt.)` (6) |
| 8 | on | 0 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (2), `spawn_warrior_when_none_left` (2) | none | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking (opt.)` (6) |
| 8 | on | 5 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (2), `spawn_warrior_when_none_left` (2) | none | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking (opt.)` (6) |
| 8 | on | 10 | `eat_regularly` (6), `leave_cave_in_time (opt.)` (6), `game_is_won` (2), `spawn_warrior_when_none_left` (2) | none | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking (opt.)` (6) |

### Observations and the chosen parameters

* **Dragon HP 100 (instead of 50)** makes the game long enough that every warrior has to eat several times.
* **N = 6 rather than 8:** the warriors return to eat more often. `staggered_meals` then needs about 21 steps instead of 18, and the greedy baselines violate the meal constraints in both initial-wheat situations (with N = 8, only `greedy_eat_last` fails, in one of them).
  * N = 5 turned out to be too tight in earlier experiments: even `staggered_meals` then violated `keep_attacking` and occasionally lost.
* **Weakness on:** without it, ignoring the meals is a viable "exploit".
  * Without weakness, `greedy_no_meals` lets the warriors starve while attacking, keeps spawning new ones, and wins 30 % of the games at N = 6 (80 % at N = 8).
  * When it wins, it wins faster than any baseline that respects the meals: 14.3 steps against 19.5–22.5 at N = 6.
  * Its success is not reliable, though, and it violates the constraints in every situation.
  * With weakness on (and N = 6), starving warriors deal no damage, and the strategy never wins.

  Without weakness, the game can be won without following the intended strategy. This shows that the functional constraints check more than the outcome: they check that the AM behaves according to the strategy.
* **R = 5.** Regeneration has almost no effect on the strategies that keep attacking: `staggered_meals` needs only 0.4 steps more with R = 5 than with R = 0. Its effects are elsewhere:
  * it slows down attacks in waves (`assemble_and_strike` needs 20.5 steps with R = 5 against 18.8 with R = 0);
  * it makes failed attempts clearly visible: a losing `greedy_no_meals` leaves the Dragon with 92 of 100 HP with R = 5, against 23 HP with R = 0.

  It also gives the reason in the story for the `keep_attacking` constraint (never leave the Dragon unattacked for more than 2 steps in a row). Of the baselines, only `assemble_and_strike` violates that constraint, even though it wins about as fast as `staggered_meals`.
* **Larger waves did not remove the gaps** of `assemble_and_strike` (earlier experiments with 6 and 8 warriors). With N = 6, one wave can attack for only about 3 steps, so several waves are needed anyway. With larger waves, the first attack also comes too late for the "attack in the first 15 steps" constraint.
* **Spawning before eating (`greedy_eat_last`).** With the default initial wheat (10), this mistake never shows: no meal is ever missing wheat.
  * With other initial amounts of wheat (2 farmers and 1 warrior), the mistake appeared for most of the amounts we tried between 0 and 40 (e.g. 12, 15, 25 or 34); only 10 and a few others avoided it. A villager returns to eat, but the wheat was already spent on spawning.
  * The test situations `initial_wheat=15` and `initial_wheat=15,seed=1` therefore start with 15 wheat (with the default seed 42 and with seed 1). With 15 wheat, both greedy variants fail for every seed we tried (42, 1, 2, 3). Two seeds with the same amount also hint that the amount of wheat is the problem. The system constraints catch the mistake ("Not enough wheat for a meal", and a villager without an assignment), and so do `eat_regularly` and, one step earlier, `keep_wheat_reserve`.
  * `greedy_with_meals` checks the wheat before eating, but keeps no reserve, so it also runs out of wheat for some meals with such initial amounts. In `initial_wheat=15`, at step 5 the two farmers spawn a new farmer and leave 1 wheat. At step 6, three villagers must eat (both farmers and the warrior who has just returned), but there is wheat for only one meal. The second farmer farms instead and eats one step late. The warrior has no wheat for a meal, so the AM sends them back to the Cave; they starve for two steps and violate `no_pointless_trip_to_cave` and `attack_after_moving_to_cave` as well. `keep_wheat_reserve` reports the cause already at step 5 (1 wheat left, but 3 villagers have to eat in the next step).
  * `greedy_with_reserve` keeps a constant reserve of wheat for the meals, and spawns only from the wheat above it.
    * With a reserve of 3 wheat, it passes all the test situations and wins all 10 games in 22.5 steps on average, against 19.8 steps for `greedy_with_meals`. The price is slower spawning.
    * Over initial amounts of 0–40 wheat (seeds 42 and 1–3), it violated `eat_regularly` only with 19 wheat, in 2 of the 4 seeds. 3 wheat is not always enough for all the meals that are due at the same time, but none of the test situations shows it.
    * With a reserve of 5 wheat, it never starved a villager, but it won only 90 % of the games, in 24.0 steps.
* **`no_pointless_trip_to_cave`.** It reports a warrior sent to the Cave too hungry to attack even once before returning to eat. It fires at the step of the mistake, which can be earlier than the resulting `eat_regularly` violation, or even without one (the warrior returns and eats in time, but the trip was useless).
  * Among the baselines, it is violated only by the greedy ones, in the initial-wheat situations. It never fires for `staggered_meals` or `assemble_and_strike`.
  * It is an example of a constraint that FCL cannot check directly: whether the trip can still be useful depends on the future. The constraint uses a necessary condition based on the meal counter.
* **Changes after the first LLM pilot.** In the AMs that won every game but violated the constraints, all the starvation had one of two causes. Either a warrior left the Cave too late (one or two steps), or the wheat for a meal had been spent on spawning.
  * `eat_regularly` now states the rule itself (`steps_since_meal < MEAL_INTERVAL`, i.e. no villager is starving), instead of "a villager that has not eaten for 5 steps must eat now". The old form reported a warrior who was still in the Cave as "must eat now", which they could not do.
  * The new `leave_cave_in_time` reports the late departure at the step where the mistake is made: a villager in the Cave with `steps_since_meal >= MEAL_INTERVAL - 2` must go to the Village.
  * `keep_attacking` counts a step without an attack only when at least two warriors are alive. Almost all its violations by the winning AMs happened in the opening, when the single initial warrior went to eat (or was killed) before reinforcements arrived. In that phase the Dragon only regenerates from about 94 back to 100 HP.
  * Re-checking the pilot AMs with the new constraints: 16 instead of 7 of the 192 AMs pass all constraints. The 9 newly valid AMs had violated only `keep_attacking` in the opening. All AMs that starve villagers still fail.
* **Changes after the second LLM pilot.** In 261 of the 876 test situations of the pilot AMs (146 AMs × 6 situations), the game was lost and `game_is_won` was the only violated required constraint, so the feedback did not say why the game was lost. Typical causes: the AM spawned exactly the required two warriors and then hoarded wheat while they died, or it spent the wheat on spawning right before a warrior returned to eat.
  * `spawn_at_least_a_few_warriors` was replaced by `spawn_warrior_when_none_left`: when there are no warriors, a new one must be spawned within 5 steps.
  * New `spawn_when_enough_wheat`: if there is enough wheat for a Warrior (12) plus a reserve of one meal for every villager, and at least two farmers are not eating, a new villager must be spawned in this step (not checked in the last 5 steps). The threshold uses the Warrior cost, so an AM saving for a Warrior is not forced to spawn a Farmer.
  * New `keep_wheat_reserve`: the wheat left after the step (computed from the assignments: meals and spawning consume wheat, farming produces it) must cover the meals of the villagers who have to eat in the next step. It reports a wheat shortage one or more steps before `eat_regularly`. Spawning at the `spawn_when_enough_wheat` threshold never violates it.
  * `attack_after_moving_to_cave` now requires 2 attacks within 4 steps after moving to the Cave (instead of 1 attack before the end of the game). It assumes a warrior who has just eaten (they can attack up to 3 times before returning). `staggered_meals` now staggers the meals only one attack earlier, so that every trip has at least two attacks; it also wins slightly faster (20.7 instead of 21.6 steps).
  * The Dragon killed in the last step (30) was reported as a `game_is_won` violation, because the constraints are checked before each step is executed. The FCL monitor now evaluates the obligations that reach the end of the run also in the final state after the last step (see [`fcl/README.md`](../fcl/README.md)). This removed 17 false violations in the pilot.
  * With these changes, only 16 of the 433 lost situations of the pilot AMs have `game_is_won` as the only violated required constraint. The optional constraints explain only 3 of them, so the next experiments use only the required constraints (the optional ones are kept in the DSL, but not in the prompts).
  * The prompt now also offers `environment.warriors` and `environment.farmers` (all villagers, with their `location`), e.g. for planning the wheat reserve for the warriors returning from the Cave.
