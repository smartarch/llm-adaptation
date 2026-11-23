Here is a report from running unit tests on your implementation:

............................F...FF.FF.Fssssssssssss                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Only 0 wheat will be left after step 16 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Jeff). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 17 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Deborah). Keep enough wheat in reserve for the meals that are due.
Only 0 wheat will be left after step 18 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Jeff). Keep enough wheat in reserve for the meals that are due.
(violated 3 times in total, at steps 16, 17, 18)

Villager Jeff has not eaten for 6 steps, so they are starving (step 18). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Only 0 wheat will be left after step 20 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Jeff). Keep enough wheat in reserve for the meals that are due.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
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
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: seed=2, initial_wheat=15
6 failed, 33 passed, 12 skipped in 5.92s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 33%. The average number of turns (steps) to win was 18.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
