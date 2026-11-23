Here is a report from running unit tests on your implementation:

............................F...F......ssssssssssss                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Only 0 wheat will be left after step 17 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (John). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 18 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Richard). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 19 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (John). Keep enough wheat in reserve for the meals that are due.
(violated 3 times in total, at steps 17, 18, 19)

Villager John has not eaten for 6 steps, so they are starving (step 19). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Only 0 wheat will be left after step 20 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Thomas). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 21 (after the meals, spawning and farming in this step), but 2 villagers will have to eat in the next step (Michelle, Charles). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 22 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Thomas). Keep enough wheat in reserve for the meals that are due.
(violated 3 times in total, at steps 20, 21, 22)

Villager Thomas has not eaten for 6 steps, so they are starving (step 22). Every villager must eat at least once in every 6 consecutive steps.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=2, initial_wheat=15,seed=1
 - passed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
2 failed, 37 passed, 12 skipped in 2.45s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 25.7 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
