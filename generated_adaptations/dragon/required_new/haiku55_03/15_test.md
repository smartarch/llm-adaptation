Here is a report from running unit tests on your implementation:

...........................F...FF..F...ssssssssssss                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Villager Richard has not eaten for 4 steps and is still in the Cave (step 28). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
Villager Paul has not eaten for 4 steps and is still in the Cave (step 18). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager Elizabeth has not eaten for 4 steps and is still in the Cave (step 25). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
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
 - failed for: seed=1, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2, seed=3, no_initial_warriors
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
4 failed, 35 passed, 12 skipped in 1.37s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 67%. The average number of turns (steps) to win was 24.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
