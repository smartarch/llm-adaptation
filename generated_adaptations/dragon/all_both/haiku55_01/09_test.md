Here is a report from running unit tests on your implementation:

...........................FFFFFF......                                  [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
Villager Maria has not eaten for 5 steps and must eat now (step 6), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 14), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 20), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 21), so it regenerates its health. Keep attacking it without longer breaks.
(violated 12 times in total, at steps 14, 20, 21, 22, 23, 24, 25, 26, 27, 28, ...)

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Villager Maria has not eaten for 5 steps and must eat now (step 6), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 21), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
(violated 7 times in total, at steps 21, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
The Dragon was not attacked for more than 2 steps in a row (step 14), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 15), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 16), so it regenerates its health. Keep attacking it without longer breaks.
(violated 17 times in total, at steps 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, ...)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
The Dragon was not attacked for more than 2 steps in a row (step 22), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 27), so it regenerates its health. Keep attacking it without longer breaks.
(violated 6 times in total, at steps 22, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
The Dragon was not attacked for more than 2 steps in a row (step 19), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 20), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 21), so it regenerates its health. Keep attacking it without longer breaks.
(violated 12 times in total, at steps 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, ...)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
The Dragon was not attacked for more than 2 steps in a row (step 12), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 18), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 19), so it regenerates its health. Keep attacking it without longer breaks.
(violated 14 times in total, at steps 12, 18, 19, 20, 21, 22, 23, 24, 25, 26, ...)

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
6 failed, 33 passed in 2.47s

Update your code to fix the failing tests.
