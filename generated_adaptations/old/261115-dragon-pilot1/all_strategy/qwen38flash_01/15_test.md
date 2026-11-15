Here is a report from running unit tests on your implementation:

...............FFFFFFFFFFFFFFFFFF......                                  [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Steven" to "spawn warrior".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Steven" to "spawn warrior".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Margaret" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Sarah" to "eat".
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Steven" to "spawn warrior".
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Steven" to "spawn warrior".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat to spawn new villager. Cannot assign "Steven" to "spawn warrior".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Steven (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Steven (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Margaret (Warrior), Sarah (Warrior)
Each component must be assigned exactly once.
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Steven (Farmer)
Each component must be assigned exactly once.
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': Steven (Farmer)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Steven (Farmer)
Each component must be assigned exactly once.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
Villager Ruth has not eaten for 5 steps and must eat now (step 21), otherwise they starve.
Villager Paul has not eaten for 5 steps and must eat now (step 22), otherwise they starve.
(violated 2 times in total, at steps 21, 22)

Warrior Dorothy should go to the Cave to attack the Dragon.
Warrior David should go to the Cave to attack the Dragon.
Warrior John should go to the Cave to attack the Dragon.
(violated 39 times in total, at steps 30)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Warrior Dorothy should go to the Cave to attack the Dragon.
Warrior David should go to the Cave to attack the Dragon.
Warrior John should go to the Cave to attack the Dragon.
(violated 30 times in total, at steps 30)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
The Dragon was not attacked for more than 2 steps in a row (step 16), so it regenerates its health. Keep attacking it without longer breaks.

Warrior David should go to the Cave to attack the Dragon.
Warrior John should go to the Cave to attack the Dragon.
Warrior Betty should go to the Cave to attack the Dragon.
(violated 38 times in total, at steps 30)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
Villager Margaret has not eaten for 5 steps and must eat now (step 27), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 28), so it regenerates its health. Keep attacking it without longer breaks.

Warrior David should go to the Cave to attack the Dragon.
Warrior Margaret should go to the Cave to attack the Dragon.
Warrior John should go to the Cave to attack the Dragon.
(violated 17 times in total, at steps 30)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager Patricia has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
Villager Paul has not eaten for 5 steps and must eat now (step 9), otherwise they starve.
(violated 2 times in total, at steps 6, 9)

The Dragon was not attacked for more than 2 steps in a row (step 13), so it regenerates its health. Keep attacking it without longer breaks.

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

Warrior Sarah should go to the Cave to attack the Dragon.
Warrior Dorothy should go to the Cave to attack the Dragon.
(violated 8 times in total, at steps 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
Villager Patricia has not eaten for 5 steps and must eat now (step 6), otherwise they starve.

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

Warrior Dorothy should go to the Cave to attack the Dragon.
(violated 3 times in total, at steps 30)

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
18 failed, 21 passed in 2.77s

Update your code to fix the failing tests.
