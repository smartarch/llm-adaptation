Here is a report from running unit tests on your implementation:

................FFFFF.FFFFFssssssssssss                                  [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Jennifer" to "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Steven" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Sarah" to "eat".
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Mary" to "eat".
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Sarah" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Karen" to "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Karen" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Jennifer (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Steven (Farmer), Sarah (Farmer)
Each component must be assigned exactly once.
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Mary (Warrior)
Each component must be assigned exactly once.
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': Sarah (Farmer), Karen (Warrior)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Karen (Warrior)
Each component must be assigned exactly once.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1
10 failed, 17 passed, 12 skipped in 0.79s

Update your code to fix the failing tests.
