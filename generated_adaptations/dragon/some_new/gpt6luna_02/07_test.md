Here is a report from running unit tests on your implementation:

...............................FF.FFF.F...F....FF..                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
Villager Kenneth has not eaten for 6 steps, so they are starving (step 15). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager Michelle has not eaten for 6 steps, so they are starving (step 18). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=2] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[seed=3] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated_at_the_end[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
There were no Warriors at step 1, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.

At step 12, there was 24 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 15, there was 38 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
At step 18, there was 46 wheat, which is enough to spawn a new villager and still keep a reserve of one meal for every villager. When there are fewer than 5 villagers, enough wheat and free farmers, two Farmers should spawn a new villager instead of farming.
(violated 4 times in total, at steps 12, 15, 18, 24)
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[seed=3] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated_at_the_end[no_initial_warriors] _
There were no Warriors at step 25, so nobody could attack the Dragon, but no new Warrior was spawned in the next 5 steps. When there are no Warriors, a new Warrior should be spawned soon.
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
 - failed for: initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=2, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: seed=1, initial_wheat=15
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: no_initial_warriors
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - failed for: seed=3, no_initial_warriors
 - passed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
9 failed, 42 passed in 4.74s

Update your code to fix the failing tests. Only the system and required tests need to be fixed, the optional tests are just hints for improving your solution.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
