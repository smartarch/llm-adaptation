Here is a report from running unit tests on your implementation:

...FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFssssssssssss                      [100%]
================================== FAILURES ===================================
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
____________ TestAdaptSystem.test_no_repeated_assignments[seed=2] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
____________ TestAdaptSystem.test_no_repeated_assignments[seed=3] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
______ TestAdaptSystem.test_no_repeated_assignments[no_initial_warriors] ______
NameError on line 60 in _apply: name 'environment_assign' is not defined
_______ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15] ________
NameError on line 60 in _apply: name 'environment_assign' is not defined
____ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15,seed=1] ____
NameError on line 60 in _apply: name 'environment_assign' is not defined
_______________ TestAdaptSystem.test_no_invalid_groups[seed=1] ________________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_______________ TestAdaptSystem.test_no_invalid_groups[seed=2] ________________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_______________ TestAdaptSystem.test_no_invalid_groups[seed=3] ________________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_________ TestAdaptSystem.test_no_invalid_groups[no_initial_warriors] _________
NameError on line 60 in _apply: name 'environment_assign' is not defined
__________ TestAdaptSystem.test_no_invalid_groups[initial_wheat=15] ___________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_______ TestAdaptSystem.test_no_invalid_groups[initial_wheat=15,seed=1] _______
NameError on line 60 in _apply: name 'environment_assign' is not defined
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
NameError on line 60 in _apply: name 'environment_assign' is not defined
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
NameError on line 60 in _apply: name 'environment_assign' is not defined
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
NameError on line 60 in _apply: name 'environment_assign' is not defined
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
NameError on line 60 in _apply: name 'environment_assign' is not defined
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
NameError on line 60 in _apply: name 'environment_assign' is not defined
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
NameError on line 60 in _apply: name 'environment_assign' is not defined
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
NameError on line 60 in _apply: name 'environment_assign' is not defined
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
NameError on line 60 in _apply: name 'environment_assign' is not defined
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
NameError on line 60 in _apply: name 'environment_assign' is not defined
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
NameError on line 60 in _apply: name 'environment_assign' is not defined
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
NameError on line 60 in _apply: name 'environment_assign' is not defined
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
NameError on line 60 in _apply: name 'environment_assign' is not defined
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
NameError on line 60 in _apply: name 'environment_assign' is not defined
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
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
36 failed, 3 passed, 12 skipped in 0.64s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
