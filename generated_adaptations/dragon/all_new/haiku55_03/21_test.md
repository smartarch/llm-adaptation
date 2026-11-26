Here is a report from running unit tests on your implementation:

.................................FFFFFFFF.FF.FFFFFF                      [100%]
================================== FAILURES ===================================
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
At step 5, there was 16 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
At step 5, there was 16 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
Warrior Deborah moved to the Cave at step 16, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
Warrior Kenneth moved to the Cave at step 16, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=1] _
Warrior Elizabeth should go to the Cave to attack the Dragon.
(violated 5 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=2] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
Warrior Deborah should go to the Cave to attack the Dragon.
(violated 11 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15] _
Warrior Kenneth should go to the Cave to attack the Dragon.
Warrior Deborah should go to the Cave to attack the Dragon.
Warrior Elizabeth should go to the Cave to attack the Dragon.
(violated 24 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
Warrior Carol should go to the Cave to attack the Dragon.
(violated 2 times in total, at steps 30)

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
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15
 - passed for: seed=3, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
16 failed, 35 passed in 6.53s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
