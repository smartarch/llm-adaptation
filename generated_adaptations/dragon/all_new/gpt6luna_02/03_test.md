Here is a report from running unit tests on your implementation:

...FFFFFF........................F.FFFFFFFFFFF.FFFF                      [100%]
================================== FAILURES ===================================
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=2] _____________
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=3] _____________
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
______ TestAdaptSystem.test_no_repeated_assignments[no_initial_warriors] ______
In 'assign_in_village', 1 components were assigned more than once. Each component must be assigned exactly once.
_______ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15] ________
In 'assign_in_village', 3 components were assigned more than once. Each component must be assigned exactly once.
____ TestAdaptSystem.test_no_repeated_assignments[initial_wheat=15,seed=1] ____
In 'assign_in_village', 3 components were assigned more than once. Each component must be assigned exactly once.
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
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=1] __
Farmer Michelle should stay in the Village.
Farmer Donna should stay in the Village.
(violated 5 times in total, at steps 8, 9, 10, 14)

Warrior Brian moved to the Cave at step 25, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Brian moved to the Cave at step 27, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 2 times in total, at steps 28, 30)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
Farmer Michelle should stay in the Village.
Farmer Donna should stay in the Village.
(violated 9 times in total, at steps 8, 9, 10, 19, 20, 21)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=3] __
Farmer Michelle should stay in the Village.
Farmer Donna should stay in the Village.
(violated 10 times in total, at steps 8, 9, 10, 21, 30)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
Warrior Margaret moved to the Cave at step 16, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Margaret moved to the Cave at step 18, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Margaret moved to the Cave at step 21, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 4 times in total, at steps 19, 21, 24, 26)

Farmer Donna should stay in the Village.
Farmer Michelle should stay in the Village.
(violated 9 times in total, at steps 23, 24, 25, 28, 29, 30)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
Farmer Michelle should stay in the Village.
Farmer Donna should stay in the Village.
(violated 9 times in total, at steps 4, 5, 20, 21, 25, 26, 27)

Warrior Sandra moved to the Cave at step 14, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Sandra moved to the Cave at step 16, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Sandra moved to the Cave at step 19, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 6 times in total, at steps 17, 19, 22, 24, 27, 30)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
Farmer Michelle should stay in the Village.
Farmer Donna should stay in the Village.
(violated 10 times in total, at steps 4, 5, 14, 15, 16, 20)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=1] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
Warrior Lisa moved to the Cave at step 26, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Lisa moved to the Cave at step 29, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 2 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15] _
Warrior Sandra moved to the Cave at step 29, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
At least one new farmer should be spawned to increase the chance of killing the Dragon.
================================ Test Results =================================
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
22 failed, 29 passed in 8.97s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 33%. The average number of turns (steps) to win was 23.0 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
