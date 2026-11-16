Here is a report from running unit tests on your implementation:

...........................FFFFFF.........F........                      [100%]
================================== FAILURES ===================================
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=1] __
At least two new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=2] __
At least two new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[seed=3] __
At least two new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[no_initial_warriors] _
At least two new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15] _
At least two new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptRequiredConstraints.test_no_required_constraints_violated[initial_wheat=15,seed=1] _
At least two new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.

At least one new farmer should be spawned to increase the chance of killing the Dragon.
_ TestAdaptOptionalConstraints.test_no_optional_constraints_violated[no_initial_warriors] _
The Dragon should be attacked at least once in the first 15 steps of the game.
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
TestAdaptOptionalConstraints::test_no_optional_constraints_violated:
 - failed for: no_initial_warriors
 - passed for: seed=1, seed=2, seed=3, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptOptionalConstraints::test_no_optional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptRequiredConstraints::test_no_required_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
7 failed, 44 passed in 3.05s

Update your code to fix the failing tests.
