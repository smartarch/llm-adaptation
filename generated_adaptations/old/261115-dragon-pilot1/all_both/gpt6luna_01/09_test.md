Here is a report from running unit tests on your implementation:

....................F.....F.....F......                                  [100%]
================================== FAILURES ===================================
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Elizabeth" to "eat".
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Elizabeth (Farmer)
Each component must be assigned exactly once.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
Villager Elizabeth has not eaten for 5 steps and must eat now (step 13), otherwise they starve.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15
TestAdaptSystem::test_all_assigned:
 - failed for: initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
3 failed, 36 passed in 2.28s

Update your code to fix the failing tests.
