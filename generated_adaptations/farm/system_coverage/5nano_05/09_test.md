Here is a report from running unit tests on your implementation:

...F.FF.F......ssssss                                                    [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
There were 56 assignment errors in total.
________ TestAdaptSystem.test_no_assignment_errors[some_moving_drones] ________
There were 8 assignment errors in total.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
In 'assign_drones', 8 components were assigned more than once. Each component must be assigned exactly once.
______ TestAdaptSystem.test_no_repeated_assignments[some_moving_drones] _______
In 'assign_drones', 8 components were assigned more than once. Each component must be assigned exactly once.
================================ Test Results =================================
TestAdaptSystem::test_no_assignment_errors:
 - failed for: seed=1, some_moving_drones
 - passed for: all_protecting
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, some_moving_drones
 - passed for: all_protecting
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, all_protecting, some_moving_drones
4 failed, 11 passed, 6 skipped in 1.81s

Update your code to fix the failing tests.
