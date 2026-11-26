Here is a report from running unit tests on your implementation:

.....................FF...FFFFFFFFFFFFFssssssssssss                      [100%]
================================== FAILURES ===================================
__________________ TestAdaptSystem.test_all_assigned[seed=1] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Donna (Farmer)
Each component must be assigned exactly once.
__________________ TestAdaptSystem.test_all_assigned[seed=2] __________________
The following components have not been assigned to a group:
- in 'assign_in_village': Susan (Farmer), Donna (Farmer)
Each component must be assigned exactly once.
_________ TestAdaptSystem.test_all_assigned[initial_wheat=15,seed=1] __________
The following components have not been assigned to a group:
- in 'assign_in_village': Donna (Farmer)
Each component must be assigned exactly once.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
Villager Christopher has not eaten for 4 steps and is still in the Cave (step 5). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Joseph has not eaten for 4 steps and is still in the Cave (step 13). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Donna has not eaten for 4 steps and is still in the Cave (step 25). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 4 times in total, at steps 5, 13, 25, 26)

Villager Christopher has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Donna has not eaten for 6 steps, so they are starving (step 27). Every villager must eat at least once in every 6 consecutive steps.
Villager Donna has not eaten for 7 steps, so they are starving (step 28). Every villager must eat at least once in every 6 consecutive steps.
(violated 3 times in total, at steps 7, 27, 28)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
Villager Christopher has not eaten for 4 steps and is still in the Cave (step 5). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Richard has not eaten for 4 steps and is still in the Cave (step 7). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Daniel has not eaten for 4 steps and is still in the Cave (step 11). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 10 times in total, at steps 5, 7, 11, 12, 13, 14, 25, 26)

Villager Christopher has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Richard has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager Daniel has not eaten for 6 steps, so they are starving (step 13). Every villager must eat at least once in every 6 consecutive steps.
(violated 9 times in total, at steps 7, 9, 13, 15, 16, 27, 28)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
Villager Christopher has not eaten for 4 steps and is still in the Cave (step 5). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Joseph has not eaten for 4 steps and is still in the Cave (step 13). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Joseph has not eaten for 4 steps and is still in the Cave (step 20). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 7 times in total, at steps 5, 13, 20, 25, 26)

Villager Joseph has not eaten for 6 steps, so they are starving (step 15). Every villager must eat at least once in every 6 consecutive steps.
Villager Susan has not eaten for 6 steps, so they are starving (step 27). Every villager must eat at least once in every 6 consecutive steps.
Villager Donna has not eaten for 6 steps, so they are starving (step 27). Every villager must eat at least once in every 6 consecutive steps.
(violated 3 times in total, at steps 15, 27)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
Villager Richard has not eaten for 4 steps and is still in the Cave (step 12). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Daniel has not eaten for 4 steps and is still in the Cave (step 13). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Richard has not eaten for 4 steps and is still in the Cave (step 19). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 3 times in total, at steps 12, 13, 19)

Villager Richard has not eaten for 6 steps, so they are starving (step 14). Every villager must eat at least once in every 6 consecutive steps.
Villager Daniel has not eaten for 6 steps, so they are starving (step 15). Every villager must eat at least once in every 6 consecutive steps.
(violated 2 times in total, at steps 14, 15)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
Villager Christopher has not eaten for 4 steps and is still in the Cave (step 5). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Richard has not eaten for 4 steps and is still in the Cave (step 7). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Daniel has not eaten for 4 steps and is still in the Cave (step 9). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 7 times in total, at steps 5, 7, 9, 13, 16, 25, 26)

Villager Christopher has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Richard has not eaten for 6 steps, so they are starving (step 9). Every villager must eat at least once in every 6 consecutive steps.
Villager Daniel has not eaten for 6 steps, so they are starving (step 11). Every villager must eat at least once in every 6 consecutive steps.
(violated 5 times in total, at steps 7, 9, 11, 15, 27)
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
Villager Christopher has not eaten for 4 steps and is still in the Cave (step 5). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Richard has not eaten for 4 steps and is still in the Cave (step 7). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
Villager Joseph has not eaten for 4 steps and is still in the Cave (step 13). Moving to the Village takes one step, so they should go to the Village now to be able to eat in time.
(violated 7 times in total, at steps 5, 7, 13, 16, 23, 25, 26)

Villager Christopher has not eaten for 6 steps, so they are starving (step 7). Every villager must eat at least once in every 6 consecutive steps.
Villager Nancy has not eaten for 6 steps, so they are starving (step 18). Every villager must eat at least once in every 6 consecutive steps.
Villager Donna has not eaten for 6 steps, so they are starving (step 27). Every villager must eat at least once in every 6 consecutive steps.
(violated 4 times in total, at steps 7, 18, 27, 28)
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
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - failed for: seed=1, seed=2, initial_wheat=15,seed=1
 - passed for: seed=3, no_initial_warriors, initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
15 failed, 24 passed, 12 skipped in 1.35s

Update your code to fix the failing tests.

We also evaluated your code in a simulation of the game. You achieved a win rate of 0%. The average number of turns (steps) to win was N/A (only the won games are counted, N/A if all games are lost).

Try to improve your code or come up with a different approach to win the game in fewer turns.
