Here is a report from running unit tests on your implementation:

..FF........F..                                                                                                                                          [100%]
=================================================================== short test summary info ===================================================================
FAILED TestAdapt::test_no_assignment_errors - AssertionError: There were 13 assignment errors: ['Component already assigned: Drone_1', 'Component already ass...
FAILED TestAdapt::test_no_repeated_assignments - AssertionError: 13 components were assigned more than once. Each component must be assigned exactly once.
FAILED TestFarm::test_not_all_drones_are_idle[0-0] - AssertionError: All drones are idle, no drones were assigned to fields.
3 failed, 12 passed in 1.43s

Update your code to fix the failing tests.
