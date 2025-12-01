Here is a report from running unit tests on your implementation:

...FFFFFFFFFFFFFFF...                                                    [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
__________ TestAdaptSystem.test_no_assignment_errors[all_protecting] __________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
________ TestAdaptSystem.test_no_assignment_errors[some_moving_drones] ________
TypeError on line 99 in assign_drones: cannot unpack non-iterable float object
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
________ TestAdaptSystem.test_no_repeated_assignments[all_protecting] _________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
______ TestAdaptSystem.test_no_repeated_assignments[some_moving_drones] _______
TypeError on line 99 in assign_drones: cannot unpack non-iterable float object
_______________ TestAdaptSystem.test_no_invalid_groups[seed=1] ________________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
___________ TestAdaptSystem.test_no_invalid_groups[all_protecting] ____________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
_________ TestAdaptSystem.test_no_invalid_groups[some_moving_drones] __________
TypeError on line 99 in assign_drones: cannot unpack non-iterable float object
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
______________ TestAdaptSystem.test_all_assigned[all_protecting] ______________
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
____________ TestAdaptSystem.test_all_assigned[some_moving_drones] ____________
TypeError on line 99 in assign_drones: cannot unpack non-iterable float object
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
_ TestAdaptFunctional.test_no_functional_constraints_violated[all_protecting] _
TypeError on line 99 in assign_drones: cannot unpack non-iterable int object
_ TestAdaptFunctional.test_no_functional_constraints_violated[some_moving_drones] _
TypeError on line 99 in assign_drones: cannot unpack non-iterable float object
================================ Test Results =================================
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_no_assignment_errors:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_no_invalid_groups:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, all_protecting, some_moving_drones
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1, all_protecting, some_moving_drones
15 failed, 6 passed in 2.00s

Update your code to fix the failing tests.
