Here is a report from running unit tests on your implementation:

...F...........F.....                                                    [100%]
================================== FAILURES ===================================
_________________ TestAdapt.test_no_assignment_errors[seed=1] _________________
There were 8 assignment errors in total.
__________ TestAdapt.test_no_functional_constraints_violated[seed=1] __________
The most threatened field should be always fully protected (step 2, Field_2, threat level 0.09, 4 drones for full protection, 0 assigned).

There are too many idle drones (5 out of 8). They can be utilized to protect other fields.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_2 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_7 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_6 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_3 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_8 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.

To keep the protection efficient, drones shouldn't change the field they are protecting too often. Drone_4 was assigned to a different field than it was previously protecting more than 75% of the time, which is too often.
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
2 failed, 19 passed in 21.12s

Update your code to fix the failing tests.
