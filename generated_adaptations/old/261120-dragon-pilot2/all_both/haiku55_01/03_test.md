Here is a report from running unit tests on your implementation:

...............FF..FFFF..FFFF..FF..................                      [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "William" to "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "William" to "eat".
________ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15] ________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Donna" to "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Donna" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': William (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': William (Warrior)
Each component must be assigned exactly once.
_____________ TestAdaptSystem.test_all_assigned[initial_wheat=15] _____________
The following components have not been assigned to a group:
- in 'assign_in_village': Donna (Farmer)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Donna (Farmer)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Villager William has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Villager William has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager William has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=3, no_initial_warriors
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=3, no_initial_warriors
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=3, no_initial_warriors
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
12 failed, 39 passed in 3.54s

Update your code to fix the failing tests.
