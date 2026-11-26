Here is a report from running unit tests on your implementation:

.............................FF....F...............                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Only 1 wheat will be left after step 30 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Dorothy, Anthony, John). Keep enough wheat in reserve for the meals that are due.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Only 1 wheat will be left after step 25 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Dorothy, Anthony). Keep enough wheat in reserve for the meals that are due.
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
 - failed for: seed=3, no_initial_warriors
 - passed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
3 failed, 48 passed in 2.44s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 67%. The average number of turns (steps) to win was 21.5 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
