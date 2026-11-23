Good job! Your code has passed all the required tests. Your solution is correct, but the report shows that it is not optimal. You can follow the hints from the optional tests to improve your solution.

Here is a report from running unit tests on your implementation:

........................................FF.F.......                      [100%]
================================== FAILURES ===================================
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
At step 8, there were 18 wheat, which is enough to spawn a new villager (even a Warrior) and still keep a reserve of one meal for every villager (6 wheat), and 3 Farmers were not eating, but no new villager was spawned. When there is enough wheat, two Farmers should spawn a new villager instead of farming.
At step 14, there were 21 wheat, which is enough to spawn a new villager (even a Warrior) and still keep a reserve of one meal for every villager (8 wheat), and 2 Farmers were not eating, but no new villager was spawned. When there is enough wheat, two Farmers should spawn a new villager instead of farming.
(violated 2 times in total, at steps 8, 14)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=3] __
At step 21, there were 19 wheat, which is enough to spawn a new villager (even a Warrior) and still keep a reserve of one meal for every villager (7 wheat), and 3 Farmers were not eating, but no new villager was spawned. When there is enough wheat, two Farmers should spawn a new villager instead of farming.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
At step 12, there were 20 wheat, which is enough to spawn a new villager (even a Warrior) and still keep a reserve of one meal for every villager (8 wheat), and 3 Farmers were not eating, but no new villager was spawned. When there is enough wheat, two Farmers should spawn a new villager instead of farming.

Warrior Sharon moved to the Cave at step 14, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Sharon moved to the Cave at step 16, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 2 times in total, at steps 17, 19)
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
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=2, seed=3, initial_wheat=15
 - passed for: seed=1, no_initial_warriors, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
3 failed, 48 passed in 6.73s


We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 23.3 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
