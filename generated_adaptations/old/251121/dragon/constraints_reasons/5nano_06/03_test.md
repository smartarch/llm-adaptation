Here is a report from running unit tests on your implementation:

...FFFF........FFFF........                                              [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
There were 6 assignment errors in total.
______________ TestAdaptSystem.test_no_assignment_errors[seed=2] ______________
There were 6 assignment errors in total.
______________ TestAdaptSystem.test_no_assignment_errors[seed=3] ______________
There were 6 assignment errors in total.
_______ TestAdaptSystem.test_no_assignment_errors[no_initial_warriors] ________
There were 6 assignment errors in total.
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Michelle (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Michelle (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Michelle (Farmer)
Each component must be assigned exactly once.
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Michelle (Farmer)
Each component must be assigned exactly once.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptFunctional::test_no_functional_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_no_assignment_errors:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
8 failed, 19 passed in 2.02s

Update your code to fix the failing tests.
