Here is a report from running unit tests on your implementation:

..................FF....FF.F.FFFF......                                  [100%]
================================== FAILURES ===================================
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Carol" to "eat".
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "John" to "eat".
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Carol (Warrior)
Each component must be assigned exactly once.
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': John (Warrior)
Each component must be assigned exactly once.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager John has not eaten for 5 steps and must eat now (step 11), otherwise they starve.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: no_initial_warriors, initial_wheat=15
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: no_initial_warriors, initial_wheat=15
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
9 failed, 30 passed in 2.53s

Update your code to fix the failing tests.
