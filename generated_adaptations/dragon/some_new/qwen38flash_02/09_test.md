Here is a report from running unit tests on your implementation:

...FFFFFF........................FFFFFFFFFFFFFFFFFF                      [100%]
================================== FAILURES ===================================
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=2] _____________
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=3] _____________
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
______ TestAdaptSystem.test_no_repeated_assignments[no_initial_warriors] ______
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
_______ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15] ________
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
____ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15,seed=1] ____
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
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
At step 2, there was 20 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 30 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 4, there was 40 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 19 times in total, at steps 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, ...)

There were no Warriors at step 10, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 11, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 15 times in total, at steps 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
At step 2, there was 20 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 30 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 4, there was 40 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 19 times in total, at steps 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, ...)

There were no Warriors at step 22, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 23, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 24, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 3 times in total, at steps 27, 28, 29)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=3] __
At step 2, there was 20 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 30 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 4, there was 40 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 19 times in total, at steps 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, ...)

There were no Warriors at step 4, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 5, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 6, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 21 times in total, at steps 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
At step 2, there was 20 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 30 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 4, there was 40 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 19 times in total, at steps 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, ...)

There were no Warriors at step 1, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 2, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 3, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 24 times in total, at steps 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
At step 1, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 2, there was 25 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 35 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 20 times in total, at steps 1, 2, 3, 4, 6, 7, 8, 9, 11, 12, ...)

There were no Warriors at step 17, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 18, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 19, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 8 times in total, at steps 22, 23, 24, 25, 26, 27, 28, 29)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
At step 1, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 2, there was 25 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 35 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 20 times in total, at steps 1, 2, 3, 4, 6, 7, 8, 9, 11, 12, ...)

There were no Warriors at step 10, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 11, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 12, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 15 times in total, at steps 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=1] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=2] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
================================ Test Results =================================
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
24 failed, 27 passed in 3.16s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
