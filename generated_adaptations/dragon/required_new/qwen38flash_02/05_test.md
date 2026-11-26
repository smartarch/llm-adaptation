Here is a report from running unit tests on your implementation:

...............F.F..FF.F..FFFF..F......ssssssssssss                      [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Carol" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Betty" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Mary" to "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Christopher" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Carol" to "eat".
____ TestAdaptSystem.test_no_invalid_assignments[initial_wheat=15,seed=1] _____
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Christopher" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Betty (Farmer), Mary (Farmer), Carol (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Christopher (Warrior), Carol (Warrior)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Christopher (Warrior)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Only 0 wheat will be left after step 24 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Carol). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 25 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Betty, Mary, Carol). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 26 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Betty, Mary, Carol). Keep enough wheat in reserve for the meals that are due.
(violated 3 times in total, at steps 24, 25, 26)

Villager Carol has not eaten for 6 steps, so they are starving (step 26). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Villager Kenneth has not eaten for 4 steps and is still in the Cave (step 17). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Carol has not eaten for 4 steps and is still in the Cave (step 18). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 2 times in total, at steps 17, 18)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Only 0 wheat will be left after step 18 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Christopher, Carol). Keep enough wheat in reserve for the meals that are due.

Villager Christopher has not eaten for 6 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
Villager Carol has not eaten for 6 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 20)

Villager Sharon has not eaten for 4 steps and is still in the Cave (step 29). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Robert has not eaten for 4 steps and is still in the Cave (step 29). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 2 times in total, at steps 29)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Only 0 wheat will be left after step 12 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Christopher). Keep enough wheat in reserve for the meals that are due.

Villager Christopher has not eaten for 6 steps, so they are starving (step 14). Every villager must eat at least once in every 6 consecutive steps.

Villager Carol has not eaten for 4 steps and is still in the Cave (step 23). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
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
 - failed for: seed=1, seed=2, seed=3, initial_wheat=15,seed=1
 - passed for: no_initial_warriors, initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
10 failed, 29 passed, 12 skipped in 1.23s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 24.3 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
