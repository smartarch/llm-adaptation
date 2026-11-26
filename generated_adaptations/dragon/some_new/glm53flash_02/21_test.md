Here is a report from running unit tests on your implementation:

...............F.F..FF.F..FF.F..FF.FFFF.....F.....F                      [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Thomas" to "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Dorothy" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Thomas" to "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Thomas" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Christopher" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Thomas (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Dorothy (Farmer), Thomas (Farmer)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Thomas (Farmer), Christopher (Warrior)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Only 1 wheat will be left after step 17 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Dorothy, Thomas). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 18 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Thomas, Richard). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 19 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Thomas, Richard). Keep enough wheat in reserve for the meals that are due.
(violated 5 times in total, at steps 17, 18, 19, 20, 21)

Villager Thomas has not eaten for 6 steps, so they are starving (step 19). Every villager must eat at least once in every 6 consecutive steps.
Villager Thomas has not eaten for 7 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
Villager Richard has not eaten for 6 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
(violated 7 times in total, at steps 19, 20, 21, 22, 23)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Only 0 wheat will be left after step 17 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Dorothy, Thomas). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 18 (after the meals, spawning and farming in this step), but 4 villagers will have to eat in the next step (Dorothy, Thomas, Mary, Richard). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 19 (after the meals, spawning and farming in this step), but 4 villagers will have to eat in the next step (Dorothy, Thomas, Mary, Richard). Keep enough wheat in reserve for the meals that are due.
(violated 9 times in total, at steps 17, 18, 19, 20, 21, 22, 23, 24, 25)

Villager Dorothy has not eaten for 6 steps, so they are starving (step 19). Every villager must eat at least once in every 6 consecutive steps.
Villager Thomas has not eaten for 6 steps, so they are starving (step 19). Every villager must eat at least once in every 6 consecutive steps.
Villager Dorothy has not eaten for 7 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
(violated 16 times in total, at steps 19, 20, 21, 22, 23, 24, 25)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Only 1 wheat will be left after step 11 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Dorothy, Thomas, Christopher). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 12 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Thomas, Christopher, Mary). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 13 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Thomas, Christopher, Mary). Keep enough wheat in reserve for the meals that are due.
(violated 11 times in total, at steps 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, ...)

Villager Thomas has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
Villager Christopher has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
Villager Thomas has not eaten for 7 steps, so they are starving (step 14). Every villager must eat at least once in every 6 consecutive steps.
(violated 16 times in total, at steps 13, 14, 15, 16, 17, 18, 19, 20, 21)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
There were no Warriors at step 22, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 23, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
There were no Warriors at step 24, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
(violated 3 times in total, at steps 27, 28, 29)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, seed=3, initial_wheat=15,seed=1
 - passed for: seed=2, no_initial_warriors, initial_wheat=15
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=3, initial_wheat=15,seed=1
 - passed for: seed=2, no_initial_warriors, initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=3, initial_wheat=15,seed=1
 - passed for: seed=2, no_initial_warriors, initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15
16 failed, 35 passed in 2.69s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 33%. The average number of turns (steps) to win was 19.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
