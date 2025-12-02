Here is a report from running unit tests on your implementation:

...F...........F.....                                                    [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
There were 2 assignment errors in total.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
Field Field_4 is overprotected (3 drones for full protection, 5 assigned), use the drones elsewhere.

Field Field_3 is overprotected (2 drones for full protection, 4 assigned), use the drones elsewhere.
================================ Test Results =================================
TestAdaptSystem::test_no_assignment_errors:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, all_protecting, some_moving_drones
2 failed, 19 passed in 13.56s

Update your code to fix the failing tests.
