Here is a report from running unit tests on your implementation:

...............F.....                                                    [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
There are too many idle drones. They can be utilized to protect other fields. At least half of the drones should be used for protection most of the time.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1
 - passed for: all_protecting, some_moving_drones
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, all_protecting, some_moving_drones
1 failed, 20 passed in 19.48s

Update your code to fix the failing tests.
