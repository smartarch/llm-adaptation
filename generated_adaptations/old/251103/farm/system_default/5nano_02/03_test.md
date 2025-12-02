Here is a report from running unit tests on your implementation:

...FFFFFF............                                                    [100%]
================================== FAILURES ===================================
_________________ TestAdapt.test_no_assignment_errors[seed=1] _________________
There were 58 assignment errors in total.
_____________ TestAdapt.test_no_assignment_errors[all_protecting] _____________
There were 2 assignment errors in total.
___________ TestAdapt.test_no_assignment_errors[some_moving_drones] ___________
There were 2 assignment errors in total.
_______________ TestAdapt.test_no_repeated_assignments[seed=1] ________________
In 'assign_drones', 4 components were assigned more than once. Each component must be assigned exactly once.
___________ TestAdapt.test_no_repeated_assignments[all_protecting] ____________
In 'assign_drones', 2 components were assigned more than once. Each component must be assigned exactly once.
_________ TestAdapt.test_no_repeated_assignments[some_moving_drones] __________
In 'assign_drones', 2 components were assigned more than once. Each component must be assigned exactly once.
================================ Test Results =================================
TestAdapt::test_no_invalid_groups:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_all_assigned:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_functional_constraints_violated:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_assignment_errors:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_repeated_assignments:
 - failed for: seed=1, all_protecting, some_moving_drones
6 failed, 15 passed in 2.90s

Update your code to fix the failing tests.
