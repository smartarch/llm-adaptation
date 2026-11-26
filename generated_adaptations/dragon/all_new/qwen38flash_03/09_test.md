Good job! Your code has passed all the required tests. Your solution is correct, but the report shows that it is not optimal. You can follow the hints from the optional tests to improve your solution.

Here is a report from running unit tests on your implementation:

.......................................F...FF..F...                      [100%]
================================== FAILURES ===================================
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=1] __
Warrior David moved to the Cave at step 21, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior David moved to the Cave at step 25, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 2 times in total, at steps 25, 28)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
At step 1, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.

Warrior David moved to the Cave at step 14, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior David moved to the Cave at step 16, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior David moved to the Cave at step 19, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 4 times in total, at steps 17, 19, 22, 24)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
At step 1, there was 15 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
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
 - failed for: seed=1, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2, seed=3, no_initial_warriors
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
4 failed, 47 passed in 3.59s


We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 25.7 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
