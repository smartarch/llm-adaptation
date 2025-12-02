Here is a report from running unit tests on your implementation:

...F...........F.....                                                    [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
There were 3 assignment errors in total.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
There are too many idle drones. They can be utilized to protect other fields. At least half of the drones should be used for protection most of the time.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_4 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_8 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.
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
2 failed, 19 passed in 7.54s

Update your code to fix the failing tests.
