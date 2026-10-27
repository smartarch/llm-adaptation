Here is a report from running unit tests on your implementation:

...........................FFFFFF......                                  [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
(violated 7 times in total, at steps 24, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Villager Susan has not eaten for 5 steps and must eat now (step 15), otherwise they starve.
Villager Jason has not eaten for 5 steps and must eat now (step 21), otherwise they starve.
(violated 2 times in total, at steps 15, 21)

The Dragon was not attacked for more than 2 steps in a row (step 23), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 30), so it regenerates its health. Keep attacking it without longer breaks.
(violated 2 times in total, at steps 23, 30)

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
Villager Susan has not eaten for 5 steps and must eat now (step 15), otherwise they starve.
Villager Susan has not eaten for 5 steps and must eat now (step 22), otherwise they starve.
(violated 2 times in total, at steps 15, 22)

The Dragon was not attacked for more than 2 steps in a row (step 17), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
(violated 8 times in total, at steps 17, 24, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
Villager William has not eaten for 5 steps and must eat now (step 11), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 23), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
(violated 8 times in total, at steps 23, 24, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager Kenneth has not eaten for 5 steps and must eat now (step 7), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 22), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 23), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
(violated 9 times in total, at steps 22, 23, 24, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
Villager Kenneth has not eaten for 5 steps and must eat now (step 7), otherwise they starve.

The Dragon was not attacked for more than 2 steps in a row (step 22), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 23), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
(violated 9 times in total, at steps 22, 23, 24, 25, 26, 27, 28, 29, 30)

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
6 failed, 33 passed in 2.84s

Update your code to fix the failing tests.
