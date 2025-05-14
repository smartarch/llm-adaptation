Here is a report from running unit tests on your implementation:

..............F                                                                                                                                          [100%]
=================================================================== short test summary info ===================================================================
PASSED TestConfiguration::test_example_is_correct
PASSED TestConfiguration::test_adaptation_exists
PASSED TestAdapt::test_no_assignment_errors
PASSED TestAdapt::test_no_repeated_assignments
PASSED TestAdapt::test_no_invalid_groups
PASSED TestAdapt::test_all_assigned
PASSED TestFarm::test_protecting_drones_are_assigned[previously_protecting=5/8]
PASSED TestFarm::test_protecting_drones_are_assigned[previously_protecting=8/8]
PASSED TestFarm::test_idle_drones_are_assigned[previously_protecting=5/8]
PASSED TestFarm::test_idle_drones_are_assigned[previously_protecting=8/8]
PASSED TestFarm::test_moving_drones_are_assigned[previously_protecting=5/8]
PASSED TestFarm::test_moving_drones_are_assigned[previously_protecting=8/8]
PASSED TestFarm::test_not_all_drones_are_idle[previously_protecting=0/8]
PASSED TestFarm::test_not_all_drones_are_idle[previously_protecting=5/8]
FAILED TestFarm::test_not_all_drones_are_idle[previously_protecting=8/8] - AssertionError: All 8 drones were assigned to the "idle" group, no drones were ass...
1 failed, 14 passed in 1.11s

Update your code to fix the failing tests.
