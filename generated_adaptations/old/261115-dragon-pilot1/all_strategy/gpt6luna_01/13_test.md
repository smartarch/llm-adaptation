Here is a report from running unit tests on your implementation:

............................FF.F.......                                  [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=2] _____
Villager Kenneth has not eaten for 5 steps and must eat now (step 15), otherwise they starve.
Villager Ruth has not eaten for 5 steps and must eat now (step 16), otherwise they starve.
(violated 2 times in total, at steps 15, 16)
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
Villager Jeff has not eaten for 5 steps and must eat now (step 19), otherwise they starve.
_ TestAdaptFunctional.test_no_functional_constraints_violated[initial_wheat=15] _
Villager Ruth has not eaten for 5 steps and must eat now (step 15), otherwise they starve.
Villager Sarah has not eaten for 5 steps and must eat now (step 16), otherwise they starve.
(violated 2 times in total, at steps 15, 16)
================================ Test Results =================================
TestAdaptSystem::test_no_repeated_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_groups:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_no_invalid_assignments:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptSystem::test_all_assigned:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated:
 - failed for: seed=2, seed=3, initial_wheat=15
 - passed for: seed=1, no_initial_warriors, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
3 failed, 36 passed in 2.22s

Update your code to fix the failing tests.
