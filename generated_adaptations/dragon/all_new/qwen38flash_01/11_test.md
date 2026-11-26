Good job! Your code has passed all the required tests. Your solution is correct, but the report shows that it is not optimal. You can follow the hints from the optional tests to improve your solution.

Here is a report from running unit tests on your implementation:

...........................................FF......                      [100%]
================================== FAILURES ===================================
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
Farmer Jason should stay in the Village.
(violated 4 times in total, at steps 23, 24, 27, 28)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
Farmer Jason should stay in the Village.
(violated 4 times in total, at steps 21, 22, 23, 24)
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
 - failed for: initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
2 failed, 49 passed in 3.76s


We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 25.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
