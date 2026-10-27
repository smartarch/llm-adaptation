Here is a report from running unit tests on your implementation:

...........................FFFFFF......                                  [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=1] _____
The Dragon was not attacked for more than 2 steps in a row (step 30), so it regenerates its health. Keep attacking it without longer breaks.

To win the game, the Dragon must be killed.
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Villager Kimberly has not eaten for 5 steps and must eat now (step 15), otherwise they starve.
Villager John has not eaten for 5 steps and must eat now (step 16), otherwise they starve.
Villager Robert has not eaten for 5 steps and must eat now (step 17), otherwise they starve.
(violated 4 times in total, at steps 15, 16, 17, 18)
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
Villager Kimberly has not eaten for 5 steps and must eat now (step 21), otherwise they starve.
Villager Kimberly has not eaten for 6 steps and must eat now (step 22), otherwise they starve.
(violated 2 times in total, at steps 21, 22)

The Dragon was not attacked for more than 2 steps in a row (step 24), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
(violated 7 times in total, at steps 24, 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
Villager Betty has not eaten for 5 steps and must eat now (step 11), otherwise they starve.
Villager Robert has not eaten for 5 steps and must eat now (step 17), otherwise they starve.
(violated 2 times in total, at steps 11, 17)

The Dragon was not attacked for more than 2 steps in a row (step 25), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 26), so it regenerates its health. Keep attacking it without longer breaks.
The Dragon was not attacked for more than 2 steps in a row (step 27), so it regenerates its health. Keep attacking it without longer breaks.
(violated 6 times in total, at steps 25, 26, 27, 28, 29, 30)

To win the game, the Dragon must be killed.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager John has not eaten for 5 steps and must eat now (step 16), otherwise they starve.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15,seed=1] _
The Dragon was not attacked for more than 2 steps in a row (step 30), so it regenerates its health. Keep attacking it without longer breaks.

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
6 failed, 33 passed in 2.59s

Update your code to fix the failing tests.
