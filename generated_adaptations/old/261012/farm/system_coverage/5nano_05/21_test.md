Here is a report from running unit tests on your implementation:

...F.FF.FF.FF.Fssssss                                                    [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
________ TestAdaptSystem.test_no_assignment_errors[some_moving_drones] ________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
______ TestAdaptSystem.test_no_repeated_assignments[some_moving_drones] _______
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
_______________ TestAdaptSystem.test_no_invalid_groups[seed=1] ________________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
_________ TestAdaptSystem.test_no_invalid_groups[some_moving_drones] __________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
____________ TestAdaptSystem.test_all_assigned[some_moving_drones] ____________
NameError on line 140 in dist2_to_field: name 'dist2' is not defined
================================ Test Results =================================
TestAdaptSystem::test_no_assignment_errors:
 - failed for: seed=1, some_moving_drones
 - passed for: all_protecting
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, some_moving_drones
 - passed for: all_protecting
TestAdaptSystem::test_no_invalid_groups:
 - failed for: seed=1, some_moving_drones
 - passed for: all_protecting
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, some_moving_drones
 - passed for: all_protecting
8 failed, 7 passed, 6 skipped in 0.65s

Update your code to fix the failing tests.
