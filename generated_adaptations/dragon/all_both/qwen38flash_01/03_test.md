Here is a report from running unit tests on your implementation:

...............FFFFFFFFFFFFFFFFFF......                                  [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Elizabeth" to "spawn farmer".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "William" to "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Elizabeth" to "spawn farmer".
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Elizabeth" to "spawn farmer".
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "George" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Christopher" to "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "George" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Christopher" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Elizabeth (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': William (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Elizabeth (Farmer)
Each component must be assigned exactly once.
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Elizabeth (Farmer)
Each component must be assigned exactly once.
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': George (Farmer), Christopher (Farmer)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': George (Farmer), Christopher (Farmer)
Each component must be assigned exactly once.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
The Dragon was not attacked for more than 2 steps in a row (step 21), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
(violated 7 times in total, at steps 21, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Villager William has not eaten for 5 steps and must eat now (step 10), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 23), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
(violated 8 times in total, at steps 23, 24, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
The Dragon was not attacked for more than 2 steps in a row (step 14), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 19), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 20), so it regenerates its health. Keep attacking it without longer breaks.
(violated 13 times in total, at steps 14, 19, 20, 21, 22, 23, 24, 25, 26, 27, ...)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
The Dragon was not attacked for more than 2 steps in a row (step 19), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 20), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 21), so it regenerates its health. Keep attacking it without longer breaks.
(violated 12 times in total, at steps 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, ...)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager George has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
Villager Christopher has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
(violated 2 times in total, at steps 6)

The Dragon was not attacked for more than 2 steps in a row (step 22), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 27), so it regenerates its health. Keep attacking it without longer breaks.
(violated 6 times in total, at steps 22, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
Villager George has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
Villager Christopher has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
(violated 2 times in total, at steps 6)

The Dragon was not attacked for more than 2 steps in a row (step 23), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 29), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 30), so it regenerates its health. Keep attacking it without longer breaks.
(violated 3 times in total, at steps 23, 29, 30)

To win the game, the Dragon must be killed.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
18 failed, 21 passed in 2.20s

Update your code to fix the failing tests.
