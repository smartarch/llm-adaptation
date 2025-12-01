Here is a report from running unit tests on your implementation:

...F..F..F..F..ssssss                                                    [100%]
================================== FAILURES ===================================
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
UnboundLocalError on line 128 in assign_drones: cannot access local variable 'fully_protected_ids' where it is not associated with a value
_______________ TestAdaptSystem.test_no_invalid_groups[seed=1] ________________
UnboundLocalError on line 128 in assign_drones: cannot access local variable 'fully_protected_ids' where it is not associated with a value
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
UnboundLocalError on line 128 in assign_drones: cannot access local variable 'fully_protected_ids' where it is not associated with a value
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
UnboundLocalError on line 128 in assign_drones: cannot access local variable 'fully_protected_ids' where it is not associated with a value
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdaptSystem::test_no_invalid_groups:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
4 failed, 11 passed, 6 skipped in 1.55s

Update your code to fix the failing tests.
