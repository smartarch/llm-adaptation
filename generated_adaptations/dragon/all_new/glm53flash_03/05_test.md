Here is a report from running unit tests on your implementation:

...........................FFFFFFFFFF..FFFFFFFFFF.F                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Jennifer has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 14). Every villager must eat at least once in every 6 consecutive steps.
(violated 10 times in total, at steps 7, 9, 14, 16, 17, 21, 23, 28, 29, 30)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Jennifer has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 6 steps, so they are starving (step 11). Every villager must eat at least once in every 6 consecutive steps.
(violated 14 times in total, at steps 7, 9, 11, 14, 15, 16, 17, 21, 22, 23, ...)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 14). Every villager must eat at least once in every 6 consecutive steps.
Villager Helen has not eaten for 6 steps, so they are starving (step 21). Every villager must eat at least once in every 6 consecutive steps.
(violated 12 times in total, at steps 7, 14, 21, 22, 23, 25, 27, 29, 30)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Villager Jennifer has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 6 steps, so they are starving (step 11). Every villager must eat at least once in every 6 consecutive steps.
Villager John has not eaten for 6 steps, so they are starving (step 15). Every villager must eat at least once in every 6 consecutive steps.
(violated 11 times in total, at steps 9, 11, 15, 17, 21, 22, 23, 24, 27, 28, ...)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 6 steps, so they are starving (step 10). Every villager must eat at least once in every 6 consecutive steps.
Villager John has not eaten for 6 steps, so they are starving (step 12). Every villager must eat at least once in every 6 consecutive steps.
(violated 15 times in total, at steps 7, 10, 12, 14, 18, 19, 21, 22, 23, 24, ...)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager Helen has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 6 steps, so they are starving (step 10). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 6 steps, so they are starving (step 17). Every villager must eat at least once in every 6 consecutive steps.
(violated 18 times in total, at steps 7, 10, 17, 19, 20, 21, 22, 23, 24, 26, ...)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=2] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=1] __
Warrior Helen moved to the Cave at step 5, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Jennifer moved to the Cave at step 7, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Helen moved to the Cave at step 12, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 9 times in total, at steps 8, 10, 15, 17, 18, 22, 24, 30)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
Warrior Helen moved to the Cave at step 5, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Jennifer moved to the Cave at step 7, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior William moved to the Cave at step 9, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 14 times in total, at steps 8, 10, 12, 15, 16, 17, 18, 22, 23, 24, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=3] __
Warrior Helen moved to the Cave at step 5, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Helen moved to the Cave at step 12, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Helen moved to the Cave at step 17, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 21 times in total, at steps 8, 15, 20, 21, 22, 23, 24, 26, 28, 29, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
Warrior Jennifer moved to the Cave at step 7, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior William moved to the Cave at step 9, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior John moved to the Cave at step 13, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 14 times in total, at steps 10, 12, 16, 18, 21, 22, 23, 24, 25, 27, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15] _
Warrior Helen moved to the Cave at step 5, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior William moved to the Cave at step 8, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior John moved to the Cave at step 10, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 24 times in total, at steps 8, 11, 13, 15, 17, 19, 20, 21, 22, 23, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[initial_wheat=15,seed=1] _
Warrior Helen moved to the Cave at step 5, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior William moved to the Cave at step 8, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior William moved to the Cave at step 15, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 32 times in total, at steps 8, 11, 18, 19, 20, 21, 22, 23, 24, 25, ...)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=1] _
Warrior David moved to the Cave at step 26, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=2] _
Warrior Edward should go to the Cave to attack the Dragon.
Warrior John should go to the Cave to attack the Dragon.
(violated 3 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
Warrior Edward should go to the Cave to attack the Dragon.
Warrior Ronald should go to the Cave to attack the Dragon.
(violated 2 times in total, at steps 30)

Warrior Daniel moved to the Cave at step 26, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Jason moved to the Cave at step 27, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Dorothy moved to the Cave at step 28, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 4 times in total, at steps 30)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
Warrior Thomas should go to the Cave to attack the Dragon.
Warrior Richard should go to the Cave to attack the Dragon.
(violated 2 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
Warrior Dorothy should go to the Cave to attack the Dragon.

Warrior Ronald moved to the Cave at step 26, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Donna moved to the Cave at step 26, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
Warrior Barbara moved to the Cave at step 28, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
(violated 5 times in total, at steps 30)
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
 - passed for: initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
21 failed, 30 passed in 11.90s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
