Here is a report from running unit tests on your implementation:

.............................F.........ssssssssssss                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
To win the game, the Dragon must be killed.

Warrior Charles should go to the Cave to attack the Dragon.
Warrior Steven should go to the Cave to attack the Dragon.
Warrior Paul should go to the Cave to attack the Dragon.
(violated 28 times in total, at steps 30)

Warrior Steven should attack the Dragon after moving to the Cave.
Warrior Paul should attack the Dragon after moving to the Cave.
Warrior Michelle should attack the Dragon after moving to the Cave.
(violated 3 times in total, at steps 30)
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
 - failed for: seed=3
 - passed for: seed=1, seed=2, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
1 failed, 38 passed, 12 skipped in 1.89s

Update your code to fix the failing tests.
