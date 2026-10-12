Here is a report from running unit tests on your implementation:

...FF.FF.FF.FF.ssssss                                                    [100%]
=================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
_________ TestAdaptSystem.test_no_repeated_assignments[all_protecting] _________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
________________ TestAdaptSystem.test_no_invalid_groups[seed=1] ________________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
____________ TestAdaptSystem.test_no_invalid_groups[all_protecting] ____________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] ______________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
_________ TestAdaptSystem.test_no_invalid_assignments[all_protecting] __________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
__________________ TestAdaptSystem.test_all_assigned[seed=1] ___________________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
______________ TestAdaptSystem.test_all_assigned[all_protecting] _______________
TypeError on line 64 in pick_candidates_for_field: 'dict' object is not callable
================================= Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, all_protecting
 - passed for: some_moving_drones
TestAdaptSystem::test_no_invalid_groups:
 - failed for: seed=1, all_protecting
 - passed for: some_moving_drones
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, all_protecting
 - passed for: some_moving_drones
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, all_protecting
 - passed for: some_moving_drones
8 failed, 7 passed, 6 skipped in 6.23s

Update your code to fix the failing tests.
