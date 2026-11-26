Here is a report from running unit tests on your implementation:

...........................FFFFFF......ssssssssssss                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Villager David has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Villager David has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
Villager Jason has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 13)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Villager Jason has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
Villager Paul has not eaten for 6 steps, so they are starving (step 24). Every villager must eat at least once in every 6 consecutive steps.
Villager Carol has not eaten for 6 steps, so they are starving (step 24). Every villager must eat at least once in every 6 consecutive steps.
(violated 3 times in total, at steps 13, 24)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Villager Jeff has not eaten for 6 steps, so they are starving (step 15). Every villager must eat at least once in every 6 consecutive steps.
Villager William has not eaten for 6 steps, so they are starving (step 15). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 15)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
Villager Jeff has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager Paul has not eaten for 6 steps, so they are starving (step 18). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 9, 18)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager Jeff has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
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
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
6 failed, 33 passed, 12 skipped in 1.38s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 100%. The average number of turns (steps) to win was 26.3 (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
