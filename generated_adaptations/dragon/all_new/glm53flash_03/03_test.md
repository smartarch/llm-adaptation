Here is a report from running unit tests on your implementation:

...............FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF                      [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Invalid group for Villager in Village: "1". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
In 'assign_in_village': Invalid group for Villager in Village: "1". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Invalid group for Villager in Village: "1". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Invalid group for Villager in Village: "1". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Invalid group for Villager in Village: "1". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
In 'assign_in_village': Invalid group for Villager in Village: "0". It must be one of "farm", "cave", "spawn farmer", "spawn warrior", "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Kenneth (Farmer), Helen (Farmer), Deborah (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Kenneth (Farmer), Helen (Farmer), Deborah (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Kenneth (Farmer), Helen (Farmer), Deborah (Warrior)
Each component must be assigned exactly once.
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Kenneth (Farmer), Helen (Farmer)
Each component must be assigned exactly once.
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': Kenneth (Farmer), Helen (Farmer), Deborah (Warrior)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Kenneth (Farmer), Helen (Farmer), Deborah (Warrior)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Villager Kenneth has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Deborah has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 7, 8, 9, 10, 11)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Villager Kenneth has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Deborah has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 7, 8, 9, 10, 11)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Villager Kenneth has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Deborah has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 7, 8, 9, 10, 11)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Villager Kenneth has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Kenneth has not eaten for 7 steps, so they are starving (step 8). Every villager must eat at least once in every 6 consecutive steps.
(violated 6 times in total, at steps 7, 8, 9)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
Villager Kenneth has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Deborah has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 7, 8, 9, 10, 11)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager Kenneth has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Deborah has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 7, 8, 9, 10, 11)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=2] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=1] __
There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 13, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 14, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 13 times in total, at steps 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 13, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 14, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 13 times in total, at steps 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=3] __
There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 13, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 14, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 13 times in total, at steps 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
There were no Warriors at step 1, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 2, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 3, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 24 times in total, at steps 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
At step 1, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 2, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 9 times in total, at steps 1, 2, 3, 4, 5, 6, 7, 8, 9)

There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 13, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 14, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 13 times in total, at steps 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
At step 1, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 2, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 9 times in total, at steps 1, 2, 3, 4, 5, 6, 7, 8, 9)

There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 13, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 14, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 13 times in total, at steps 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=1] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=2] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
36 failed, 15 passed in 4.83s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
