Here is a report from running unit tests on your implementation:

...................................FFFF........FFFF                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
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
 - failed for: seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1, seed=2
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1, seed=2
8 failed, 43 passed in 6.99s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 67%. The average number of turns (steps) to win was 26.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
