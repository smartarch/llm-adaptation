Here is a report from running unit tests on your implementation:

.............................FF........                                  [100%]
================================== FAILURES ===================================
_____ TestAdaptFunctional.test_no_functional_constraints_violated[seed=3] _____
The Dragon was not attacked for more than 2 steps in a row (step 6), so it regenerates its health. Keep attacking it without longer breaks.
_ TestAdaptFunctional.test_no_functional_constraints_violated[no_initial_warriors] _
The Dragon was not attacked for more than 2 steps in a row (step 9), so it regenerates its health. Keep attacking it without longer breaks.
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
 - failed for: seed=3, no_initial_warriors
 - passed for: seed=1, seed=2, initial_wheat=15, initial_wheat=15,seed=1
TestAdaptFunctional::test_no_functional_constraints_violated_at_the_end:
 - passed for: seed=1, seed=2, seed=3, no_initial_warriors, initial_wheat=15, initial_wheat=15,seed=1
2 failed, 37 passed in 3.33s

Update your code to fix the failing tests.
