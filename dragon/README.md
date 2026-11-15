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
| [`greedy_eat_last`](../generated_adaptations/dragon/mock/greedy_eat_last.py) | Like `greedy_with_meals`, but it decides about spawning before the meals and sends the villagers to eat without checking that there is wheat left (a likely mistake of a generated AM). Eating then fails when the wheat was spent on spawning. |
| [`staggered_meals`](../generated_adaptations/dragon/mock/staggered_meals.py) | The reference strategy. It keeps attacking continuously and staggers the warriors' meals, so that the Dragon is not left unattacked. It reserves wheat for the meals that are due, and a warrior that is too hungry eats before going to the Cave. |
| [`assemble_and_strike`](../generated_adaptations/dragon/mock/assemble_and_strike.py) | The warriors gather in the Village, eat, and attack together in waves (4 warriors, or all of them from step 10). The whole wave returns to eat together, which leaves gaps between the waves. |

## Tuning of the parameters

The parameters were tuned with [`tuning.py`](./tuning.py) (`python dragon/tuning.py`, run from the repository root). For each parameter combination and baseline, it reports:

* the win rate, the average number of steps to win, and the average remaining HP of the Dragon in lost games, over 10 runs (seeds 1–10) from the default initial state;
* the functional constraints ([`DSL/dragon_constraints.yaml`](../DSL/dragon_constraints.yaml)) violated in the 6 test situations from [`DSL/dragon.yaml`](../DSL/dragon.yaml), with the number of situations in which each was violated. The situations are seeds 1–3, `no_initial_warriors`, `initial_wheat=15` and `initial_wheat=15,seed=1` (the default setup, only with a different initial amount of wheat).

### Grid search (Dragon HP = 100, 30 steps)

The grid covers the meal interval N, the weakness flag (`hungry_cannot_attack`) and the regeneration R. The baselines are in the columns.

#### Win rate

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | 30% | 100% | 100% | 100% | 100% |
| 6 | off | 5 | 30% | 100% | 100% | 100% | 100% |
| 6 | off | 10 | 30% | 100% | 100% | 100% | 100% |
| 6 | on | 0 | 0% | 100% | 100% | 100% | 100% |
| 6 | on | 5 | 0% | 100% | 100% | 100% | 100% |
| 6 | on | 10 | 0% | 100% | 100% | 100% | 100% |
| 8 | off | 0 | 80% | 100% | 100% | 100% | 100% |
| 8 | off | 5 | 80% | 100% | 100% | 100% | 100% |
| 8 | off | 10 | 80% | 100% | 100% | 100% | 100% |
| 8 | on | 0 | 30% | 100% | 100% | 100% | 100% |
| 8 | on | 5 | 30% | 100% | 100% | 100% | 100% |
| 8 | on | 10 | 30% | 100% | 100% | 100% | 100% |

#### Average number of steps to win

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | 14.3 | 19.5 | 19.5 | 21.2 | 18.8 |
| 6 | off | 5 | 14.3 | 19.8 | 19.8 | 21.6 | 20.5 |
| 6 | off | 10 | 14.3 | 19.9 | 19.9 | 21.8 | 23.0 |
| 6 | on | 0 | n/a | 19.5 | 19.5 | 21.2 | 18.8 |
| 6 | on | 5 | n/a | 19.8 | 19.8 | 21.6 | 20.5 |
| 6 | on | 10 | n/a | 19.9 | 19.9 | 21.8 | 23.0 |
| 8 | off | 0 | 15.2 | 17.2 | 17.2 | 18.3 | 18.4 |
| 8 | off | 5 | 15.5 | 17.4 | 17.4 | 18.4 | 19.1 |
| 8 | off | 10 | 15.5 | 17.4 | 17.4 | 18.4 | 19.4 |
| 8 | on | 0 | 15.3 | 17.2 | 17.2 | 18.3 | 18.4 |
| 8 | on | 5 | 15.7 | 17.4 | 17.4 | 18.4 | 19.1 |
| 8 | on | 10 | 15.7 | 17.4 | 17.4 | 18.4 | 19.4 |

#### Average remaining HP of the Dragon in lost games

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | 23.3 | n/a | n/a | n/a | n/a |
| 6 | off | 5 | 92.0 | n/a | n/a | n/a | n/a |
| 6 | off | 10 | 100.0 | n/a | n/a | n/a | n/a |
| 6 | on | 0 | 42.1 | n/a | n/a | n/a | n/a |
| 6 | on | 5 | 100.0 | n/a | n/a | n/a | n/a |
| 6 | on | 10 | 100.0 | n/a | n/a | n/a | n/a |
| 8 | off | 0 | 25.0 | n/a | n/a | n/a | n/a |
| 8 | off | 5 | 97.5 | n/a | n/a | n/a | n/a |
| 8 | off | 10 | 100.0 | n/a | n/a | n/a | n/a |
| 8 | on | 0 | 17.3 | n/a | n/a | n/a | n/a |
| 8 | on | 5 | 79.3 | n/a | n/a | n/a | n/a |
| 8 | on | 10 | 100.0 | n/a | n/a | n/a | n/a |

#### Violated constraints (number of test situations in which the constraint was violated; generic constraints are prefixed with "system")

| N | weakness | R | `greedy_no_meals` | `greedy_with_meals` | `greedy_eat_last` | `staggered_meals` | `assemble_and_strike` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | off | 0 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (5), `spawn_at_least_a_few_farmers` (5) | `eat_regularly` (2), `no_pointless_trip_to_cave` (2) | `eat_regularly` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking` (6) |
| 6 | off | 5 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (5), `spawn_at_least_a_few_farmers` (5) | `eat_regularly` (2), `no_pointless_trip_to_cave` (2) | `eat_regularly` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking` (6) |
| 6 | off | 10 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (5), `spawn_at_least_a_few_farmers` (5) | `eat_regularly` (2), `no_pointless_trip_to_cave` (2) | `eat_regularly` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking` (6) |
| 6 | on | 0 | `eat_regularly` (6), `game_is_won` (6), `leave_cave_in_time` (6), `spawn_at_least_a_few_farmers` (6) | `eat_regularly` (2), `no_pointless_trip_to_cave` (2) | `eat_regularly` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking` (6) |
| 6 | on | 5 | `eat_regularly` (6), `game_is_won` (6), `leave_cave_in_time` (6), `spawn_at_least_a_few_farmers` (6) | `eat_regularly` (2), `no_pointless_trip_to_cave` (2) | `eat_regularly` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking` (6) |
| 6 | on | 10 | `eat_regularly` (6), `game_is_won` (6), `leave_cave_in_time` (6), `spawn_at_least_a_few_farmers` (6) | `eat_regularly` (2), `no_pointless_trip_to_cave` (2) | `eat_regularly` (2), `system: InvalidAssignmentError` (2), `system: MissingAssignmentError` (2) | none | `keep_attacking` (6) |
| 8 | off | 0 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (1) | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking` (6) |
| 8 | off | 5 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (1) | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking` (6) |
| 8 | off | 10 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (1) | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking` (6) |
| 8 | on | 0 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (2) | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking` (6) |
| 8 | on | 5 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (2) | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking` (6) |
| 8 | on | 10 | `eat_regularly` (6), `leave_cave_in_time` (6), `game_is_won` (2) | none | `eat_regularly` (1), `system: InvalidAssignmentError` (1), `system: MissingAssignmentError` (1) | none | `keep_attacking` (6) |

### Observations and the chosen parameters

* **Dragon HP 100 (instead of 50)** makes the game long enough that every warrior has to eat several times.
* **N = 6 rather than 8:** the warriors return to eat more often. `staggered_meals` then needs 21–22 steps instead of 18, and the greedy baselines violate the meal constraints in both initial-wheat situations (with N = 8, only `greedy_eat_last` fails, in one of them).
  * N = 5 turned out to be too tight in earlier experiments: even `staggered_meals` then violated `keep_attacking` and occasionally lost.
* **Weakness on:** without it, ignoring the meals is a viable "exploit".
  * Without weakness, `greedy_no_meals` lets the warriors starve while attacking, keeps spawning new ones, and wins 30 % of the games at N = 6 (80 % at N = 8).
  * When it wins, it wins faster than any baseline that respects the meals: 14.3 steps against 19.5–21.6 at N = 6.
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
  * The test situations `initial_wheat=15` and `initial_wheat=15,seed=1` therefore start with 15 wheat (with the default seed 42 and with seed 1). With 15 wheat, both greedy variants fail for every seed we tried (42, 1, 2, 3). Two seeds with the same amount also hint that the amount of wheat is the problem. The system constraints catch the mistake ("Not enough wheat for a meal", and a villager without an assignment), and so does `eat_regularly`.
  * `greedy_with_meals` (which checks the wheat but keeps no reserve) also runs out of wheat for some meals with such initial amounts.
* **`no_pointless_trip_to_cave`.** It reports a warrior sent to the Cave too hungry to attack even once before returning to eat. It fires at the step of the mistake, which can be earlier than the resulting `eat_regularly` violation, or even without one (the warrior returns and eats in time, but the trip was useless).
  * Among the baselines, it is violated only by the greedy ones, in the initial-wheat situations. It never fires for `staggered_meals` or `assemble_and_strike`.
  * It is an example of a constraint that FCL cannot check directly: whether the trip can still be useful depends on the future. The constraint uses a necessary condition based on the meal counter.
* **Changes after the first LLM pilot.** In the AMs that won every game but violated the constraints, all the starvation had one of two causes. Either a warrior left the Cave too late (one or two steps), or the wheat for a meal had been spent on spawning.
  * `eat_regularly` now states the rule itself (`steps_since_meal < MEAL_INTERVAL`, i.e. no villager is starving), instead of "a villager that has not eaten for 5 steps must eat now". The old form reported a warrior who was still in the Cave as "must eat now", which they could not do.
  * The new `leave_cave_in_time` reports the late departure at the step where the mistake is made: a villager in the Cave with `steps_since_meal >= MEAL_INTERVAL - 2` must go to the Village.
  * `keep_attacking` counts a step without an attack only when at least two warriors are alive. Almost all its violations by the winning AMs happened in the opening, when the single initial warrior went to eat (or was killed) before reinforcements arrived. In that phase the Dragon only regenerates from about 94 back to 100 HP.
  * Re-checking the pilot AMs with the new constraints: 16 instead of 7 of the 192 AMs pass all constraints. The 9 newly valid AMs had violated only `keep_attacking` in the opening. All AMs that starve villagers still fail.
