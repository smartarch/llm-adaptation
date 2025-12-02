Here is a report from running unit tests on your implementation:

...FFFFFFFF........FFFF....                                              [100%]
================================== FAILURES ===================================
______________ TestAdaptSystem.test_no_assignment_errors[seed=1] ______________
There were 63 assignment errors in total.
______________ TestAdaptSystem.test_no_assignment_errors[seed=2] ______________
There were 63 assignment errors in total.
______________ TestAdaptSystem.test_no_assignment_errors[seed=3] ______________
There were 63 assignment errors in total.
_______ TestAdaptSystem.test_no_assignment_errors[no_initial_warriors] ________
There were 64 assignment errors in total.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=1] _____________
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=2] _____________
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
____________ TestAdaptSystem.test_no_repeated_assignments[seed=3] _____________
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
______ TestAdaptSystem.test_no_repeated_assignments[no_initial_warriors] ______
In 'assign_in_village', 2 components were assigned more than once. Each component must be assigned exactly once.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
At least a few new farmers should be spawned to increase the chance of killing the dragon.

At least a few new warriors should be spawned to increase the chance of killing the dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
At least a few new farmers should be spawned to increase the chance of killing the dragon.

At least a few new warriors should be spawned to increase the chance of killing the dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
At least a few new farmers should be spawned to increase the chance of killing the dragon.

At least a few new warriors should be spawned to increase the chance of killing the dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
The Dragon should be attacked at least once in the first 15 steps of the game.

At least a few new farmers should be spawned to increase the chance of killing the dragon.

At least a few new warriors should be spawned to increase the chance of killing the dragon.

To win the game, the Dragon must be killed.
================================ Test Results =================================
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_no_assignment_errors:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptSystem::test_no_repeated_assignments:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors
12 failed, 15 passed in 1.68s

Update your code to fix the failing tests.
