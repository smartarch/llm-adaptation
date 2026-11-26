Here is a report from running unit tests on your implementation:

.................F.....F.....F...F.FF.F......F.FF.F                      [100%]
================================== FAILURES ===================================
_____________ TestAdaptSystem.test_no_invalid_assignments[seed=3] _____________
In 'assign_in_village': Not enough wheat for a meal. Cannot assign "Robert" to "eat".
__________________ TestAdaptSystem.test_all_assigned[seed=3] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Robert (Warrior)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Only 0 wheat will be left after step 28 (after the meals, spawning and farming in this step), but 1 villagers will have to eat in the next step (Robert). Keep enough wheat in reserve for the meals that are due.

Villager Robert has not eaten for 6 steps, so they are starving (step 30). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=1] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
Warrior Robert should go to the Cave to attack the Dragon.
Warrior Sharon should go to the Cave to attack the Dragon.
(violated 3 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: seed=2, initial_wheat=15
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: seed=2, initial_wheat=15
11 failed, 40 passed in 7.03s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 33%. The average number of turns (steps) to win was 26.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
