Here is a report from running unit tests on your implementation:

...................................FF..FFFF....FF..                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=1] __
At step 2, there was 20 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 30 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 4, there was 40 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 4 times in total, at steps 2, 3, 4, 6)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
At step 2, there was 20 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 3, there was 30 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 4, there was 40 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 4 times in total, at steps 2, 3, 4, 6)
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
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=3, no_initial_warriors
 - passed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
 - passed for: initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=3, no_initial_warriors
 - passed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
8 failed, 43 passed in 6.31s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 67%. The average number of turns (steps) to win was 21.5 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
