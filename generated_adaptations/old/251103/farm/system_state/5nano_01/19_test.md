Here is a report from running unit tests on your implementation:

...FFFFFFFFFFFFFFF...                                                    [100%]
================================== FAILURES ===================================
_________________ TestAdapt.test_no_assignment_errors[seed=1] _________________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
_____________ TestAdapt.test_no_assignment_errors[all_protecting] _____________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
___________ TestAdapt.test_no_assignment_errors[some_moving_drones] ___________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
_______________ TestAdapt.test_no_repeated_assignments[seed=1] ________________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
___________ TestAdapt.test_no_repeated_assignments[all_protecting] ____________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
_________ TestAdapt.test_no_repeated_assignments[some_moving_drones] __________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
__________________ TestAdapt.test_no_invalid_groups[seed=1] ___________________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
______________ TestAdapt.test_no_invalid_groups[all_protecting] _______________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
____________ TestAdapt.test_no_invalid_groups[some_moving_drones] _____________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
_____________________ TestAdapt.test_all_assigned[seed=1] _____________________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
_________________ TestAdapt.test_all_assigned[all_protecting] _________________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
_______________ TestAdapt.test_all_assigned[some_moving_drones] _______________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
__________ TestAdapt.test_no_functional_constraints_violated[seed=1] __________
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
______ TestAdapt.test_no_functional_constraints_violated[all_protecting] ______
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
____ TestAdapt.test_no_functional_constraints_violated[some_moving_drones] ____
AttributeError on line 121 in assign_drones: 'SmartFarmAdaptation' object has no attribute '_distance_to'
================================ Test Results =================================
TestAdapt::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_assignment_errors:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_repeated_assignments:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_invalid_groups:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_all_assigned:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdapt::test_no_functional_constraints_violated:
 - failed for: seed=1, all_protecting, some_moving_drones
15 failed, 6 passed in 1.72s

Update your code to fix the failing tests.
