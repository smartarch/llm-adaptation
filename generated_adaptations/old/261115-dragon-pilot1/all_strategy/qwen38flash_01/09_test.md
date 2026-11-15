Here is a report from running unit tests on your implementation:

...........................FFFFFF......                                  [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
Villager Helen has not eaten for 5 steps and must eat now (step 6), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 8), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 12), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 13), so it regenerates its health. Keep attacking it without longer breaks.
(violated 20 times in total, at steps 8, 12, 13, 14, 15, 16, 17, 18, 19, 20, ...)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

At least a few new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Villager Helen has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
Villager Helen has not eaten for 5 steps and must eat now (step 13), otherwise they starve.
(violated 2 times in total, at steps 6, 13)

The Dragon was not attacked for more than 2 steps in a row (step 8), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 15), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 21), so it regenerates its health. Keep attacking it without longer breaks.
(violated 12 times in total, at steps 8, 15, 21, 22, 23, 24, 25, 26, 27, 28, ...)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

At least a few new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
The Dragon was not attacked for more than 2 steps in a row (step 6), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 7), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 8), so it regenerates its health. Keep attacking it without longer breaks.
(violated 25 times in total, at steps 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, ...)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

At least a few new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
The Dragon should be attacked at least once in the first 15 steps of the game.

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

At least a few new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager Helen has not eaten for 5 steps and must eat now (step 6), otherwise they starve.
Villager Helen has not eaten for 5 steps and must eat now (step 13), otherwise they starve.
(violated 2 times in total, at steps 6, 13)

The Dragon was not attacked for more than 2 steps in a row (step 8), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 15), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 16), so it regenerates its health. Keep attacking it without longer breaks.
(violated 17 times in total, at steps 8, 15, 16, 17, 18, 19, 20, 21, 22, 23, ...)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

At least a few new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
Villager Helen has not eaten for 5 steps and must eat now (step 6), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 8), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 12), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 13), so it regenerates its health. Keep attacking it without longer breaks.
(violated 20 times in total, at steps 8, 12, 13, 14, 15, 16, 17, 18, 19, 20, ...)

At least a few new farmers should be spawned to increase the chance of killing the Dragon.

At least a few new warriors should be spawned to increase the chance of killing the Dragon.

To win the game, the Dragon must be killed.
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
6 failed, 33 passed in 2.40s

Update your code to fix the failing tests.
