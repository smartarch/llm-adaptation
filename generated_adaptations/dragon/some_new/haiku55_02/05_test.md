Here is a report from running unit tests on your implementation:

...................FF....FF...........F............                      [100%]
================================== FAILURES ===================================
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Ronald" to "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Ronald" to "eat".
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': Ronald (Farmer)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Ronald (Farmer)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_all_assigned:
 - failed for: initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
5 failed, 46 passed in 4.59s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 24.7 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
