Here is a report from running unit tests on your implementation:

...........................FFFF.F.......F..........                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
To win the game, the Dragon must be killed.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
To win the game, the Dragon must be killed.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[seed=2] __
Warrior Robert was sent to the Cave at step 13, but they have not eaten for 3 steps, so they will have to return to eat before they can attack the Dragon. Let them eat first.
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
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15,seed=1
 - passed for: initial_wheat=15
TestAdaptRequiredConstraints::test_no_required_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: seed=2
 - passed for: seed=1, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
6 failed, 45 passed in 5.47s

Update your code to fix the failing tests.
