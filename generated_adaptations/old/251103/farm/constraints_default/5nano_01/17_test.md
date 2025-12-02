Here is a report from running unit tests on your implementation:

...F...........F.....                                                    [100%]
================================== FAILURES ===================================
_________________ TestAdapt.test_no_assignment_errors[seed=1] _________________
There were 2 assignment errors in total.
__________ TestAdapt.test_no_functional_constraints_violated[seed=1] __________
Field Field_2 is overprotected (4 drones for full protection, 8 assigned), use the drones elsewhere.

The most threatened field should be always fully protected (step 263, Field_1, threat level 0.17, 4 drones for full protection, 2 assigned).
================================ Test Results =================================
TestAdapt::test_no_assignment_errors:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdapt::test_no_repeated_assignments:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_invalid_groups:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_all_assigned:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_functional_constraints_violated:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdapt::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, all_protecting, some_moving_drones
2 failed, 19 passed in 5.51s

Update your code to fix the failing tests.
