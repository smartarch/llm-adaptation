Here is a report from running unit tests on your implementation:

...FFFFFFFFFFFFFFFFFFFFFFFFFFFFFF......ssssssssssss                      [100%]
================================== FAILURES ===================================
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
____________ TestAdaptSystem.test_no_repeated_assignments[seed=2] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
____________ TestAdaptSystem.test_no_repeated_assignments[seed=3] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
______ TestAdaptSystem.test_no_repeated_assignments[no_initial_warriors] ______
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_______ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15] ________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
____ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15,seed=1] ____
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_______________ TestAdaptSystem.test_no_invalid_groups[seed=1] ________________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_______________ TestAdaptSystem.test_no_invalid_groups[seed=2] ________________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_______________ TestAdaptSystem.test_no_invalid_groups[seed=3] ________________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_________ TestAdaptSystem.test_no_invalid_groups[no_initial_warriors] _________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
__________ TestAdaptSystem.test_no_invalid_groups[initial_wheat=15] ___________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_______ TestAdaptSystem.test_no_invalid_groups[initial_wheat=15,seed=1] _______
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
UnboundLocalError on line 53 in spawn: cannot access local variable 'wheat' where it is not associated with a value
================================ Test Results =================================
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
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
30 failed, 9 passed, 12 skipped in 1.11s

Update your code to fix the failing tests.
