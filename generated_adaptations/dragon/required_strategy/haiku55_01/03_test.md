Here is a report from running unit tests on your implementation:

...........................F.FFFF......ssssssssssss                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
To win the game, the Dragon must be killed.

Warrior Donna should go to the Cave to attack the Dragon.
(violated 6 times in total, at steps 30)

Warrior Donna should attack the Dragon after moving to the Cave.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
To win the game, the Dragon must be killed.

Warrior Margaret should go to the Cave to attack the Dragon.
Warrior Daniel should go to the Cave to attack the Dragon.
(violated 9 times in total, at steps 30)

Warrior Margaret should attack the Dragon after moving to the Cave.
Warrior Daniel should attack the Dragon after moving to the Cave.
(violated 2 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
To win the game, the Dragon must be killed.

Warrior Margaret should go to the Cave to attack the Dragon.
Warrior Donna should go to the Cave to attack the Dragon.
(violated 17 times in total, at steps 30)

Warrior Margaret should attack the Dragon after moving to the Cave.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
To win the game, the Dragon must be killed.

Warrior Elizabeth should go to the Cave to attack the Dragon.
Warrior Daniel should go to the Cave to attack the Dragon.
Warrior Donna should go to the Cave to attack the Dragon.
(violated 31 times in total, at steps 30)

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.

Warrior Charles should go to the Cave to attack the Dragon.
(violated 7 times in total, at steps 30)

Warrior Charles should attack the Dragon after moving to the Cave.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
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
 - failed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
 - passed for: seed=2
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
5 failed, 34 passed, 12 skipped in 2.43s

Update your code to fix the failing tests.
