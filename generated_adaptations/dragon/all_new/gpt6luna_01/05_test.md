Here is a report from running unit tests on your implementation:

...................................F...F.F.....F...                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=1] __
Warrior John moved to the Cave at step 21, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=3] __
Warrior Anthony moved to the Cave at step 21, but they did not attack the Dragon at least 2 times in the next 4 steps. After moving to the Cave, a warrior should attack the Dragon at least 2 times before returning to the Village.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
Warrior Anthony should go to the Cave to attack the Dragon.
Warrior Nancy should go to the Cave to attack the Dragon.
Warrior George should go to the Cave to attack the Dragon.
(violated 15 times in total, at steps 30)
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
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=1, seed=3
 - passed for: seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
4 failed, 47 passed in 9.54s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 67%. The average number of turns (steps) to win was 23.5 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
