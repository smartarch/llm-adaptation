Here is a report from running unit tests on your implementation:

...............FF.F..FF.F..FF.F..FFFFFFssssssssssss                      [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=1] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "William" to "eat".
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=2] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Karen" to "eat".
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Brian" to "eat".
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Maria" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': William (Warrior)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Karen (Warrior)
Each component must be assigned exactly once.
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Brian (Farmer), Maria (Warrior)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Only 0 wheat will be left after step 26 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (William). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 27 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (William, Brian). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 28 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Brian, William). Keep enough wheat in reserve for the meals that are due.
(violated 5 times in total, at steps 26, 27, 28, 29, 30)

Villager William has not eaten for 6 steps, so they are starving (step 28). Every villager must eat at least once in every 6 consecutive steps.
Villager Brian has not eaten for 6 steps, so they are starving (step 29). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 7 steps, so they are starving (step 29). Every villager must eat at least once in every 6 consecutive steps.
(violated 4 times in total, at steps 28, 29, 30)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Only 0 wheat will be left after step 17 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Karen). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 18 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Karen, Sandra). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 19 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Karen, Sandra, Patricia). Keep enough wheat in reserve for the meals that are due.
(violated 7 times in total, at steps 17, 18, 19, 20, 21, 22, 23)

Villager Karen has not eaten for 6 steps, so they are starving (step 19). Every villager must eat at least once in every 6 consecutive steps.
Villager Karen has not eaten for 7 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
Villager Sandra has not eaten for 6 steps, so they are starving (step 20). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 19, 20, 21, 22, 23)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Only 1 wheat will be left after step 15 (after the meals, spawning and farming in this step), but 3 villagers will have to eat in the next step (Donald, Brian, Maria). Keep enough wheat in reserve for the meals that are due.

Villager Brian has not eaten for 6 steps, so they are starving (step 17). Every villager must eat at least once in every 6 consecutive steps.
Villager Maria has not eaten for 6 steps, so they are starving (step 17). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 17)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=2] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=1, seed=2, no_initial_warriors
 - passed for: seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, no_initial_warriors
 - passed for: seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, no_initial_warriors
 - passed for: seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
15 failed, 24 passed, 12 skipped in 2.10s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
