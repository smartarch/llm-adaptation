Here is a report from running unit tests on your implementation:

..................F.....F.....F..F.FF.Fssssssssssss                      [100%]
================================== FAILURES ===================================
______ TestAdaptSystem.test_no_invalid_assignments[no_initial_warriors] _______
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Susan" to "eat".
___________ TestAdaptSystem.test_all_assigned[no_initial_warriors] ____________
The following components have not been assigned to a group:
- in 'assign_in_village': Susan (Warrior)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Only 0 wheat will be left after step 8 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Susan). Keep enough wheat in reserve for the meals that are due.

Villager Susan has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager Susan has not eaten for 7 steps, so they are starving (step 10). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 9, 10)
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
 - failed for: no_initial_warriors
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: no_initial_warriors
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: no_initial_warriors
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: seed=2, initial_wheat=15
7 failed, 32 passed, 12 skipped in 2.10s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 33%. The average number of turns (steps) to win was 22.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
